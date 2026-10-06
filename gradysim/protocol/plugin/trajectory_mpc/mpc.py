"""
Receding-horizon double-integrator MPC core, solved as a strict quadratic program with OSQP
(through cvxpy)
"""

import logging
from typing import Tuple

import cvxpy as cp
import numpy as np

# State layout: [px, vx, py, vy, pz, vz].
# Control layout: [ux, uy, uz] 
# where each component is velocity setpoint tracked with first-order lag
_STATE_DIM = 6
_CONTROL_DIM = 3


class DoubleIntegratorMPC:
    """
    Builds a receding-horizon MPC problem once (using cvxpy Parameters, so it can be re-solved
    cheaply with warm starts) and repeatedly solves it for the latest measured state and
    reference trajectory.

    The plant model is a double integrator per axis (position, velocity), independently bounded
    on the horizontal (x, y) and vertical (z) axes, matching the structure of the
    Dynamic Velocity Mobility Handler.
    Horizontal bounds are applied per-axis (a box), not on the true norm, so the problem stays a
    strict QP solvable by OSQP

    Each axis's control input is a velocity setpoint.

    """

    def __init__(
        self,
        dt: float,
        horizon_steps: int,
        max_speed_xy_box: float,
        max_speed_z: float,
        max_acc_xy_box: float,
        max_acc_z: float,
        position_weight: float,
        velocity_weight: float,
        control_weight: float,
        control_rate_weight: float,
        terminal_position_weight: float,
        terminal_velocity_weight: float,
        tau_xy: float,
        tau_z: float,
    ):
        """
        Builds the MPC problem.

        Args:
            dt: Duration, in seconds, of each step of the prediction horizon.
            horizon_steps: Number of steps in the prediction horizon.
            max_speed_xy_box: Per-axis horizontal speed bound (m/s).
            max_speed_z: Vertical speed bound (m/s).
            max_acc_xy_box: Per-axis horizontal acceleration bound (m/s^2).
            max_acc_z: Vertical acceleration bound (m/s^2).
            position_weight: Cost weight on position tracking error at each step of the horizon.
            velocity_weight: Cost weight on velocity tracking error at each step of the horizon.
            control_weight: Cost weight on control (acceleration) effort at each step.
            control_rate_weight: Cost weight on the change in control between consecutive steps.
            terminal_position_weight: Cost weight on position tracking error at the horizon's end.
            terminal_velocity_weight: Cost weight on velocity tracking error at the horizon's end.
            tau_xy: first-order time constant (seconds) for horizontal velocity
                tracking, matching `DynamicVelocityMobilityConfiguration.tau_xy`. When set, the
                x/y control input is a velocity setpoint chased with this lag instead of a direct
                acceleration - see the class docstring.
            tau_z: first-order time constant (seconds) for vertical velocity tracking,
                matching `DynamicVelocityMobilityConfiguration.tau_z`. Same effect as `tau_xy`,
                applied to the z axis.
        """
        if dt <= 0:
            raise ValueError("dt must be > 0")
        if horizon_steps < 1:
            raise ValueError("horizon_steps must be >= 1")
        if tau_xy is not None and tau_xy <= 0:
            raise ValueError("tau_xy must be > 0 when provided")
        if tau_z is not None and tau_z <= 0:
            raise ValueError("tau_z must be > 0 when provided")

        self._dt = dt
        self._n = horizon_steps
        self._logger = logging.getLogger()

        n = horizon_steps

        # Per-axis state transition (a_block, b_block) and the linear map from (u, s) to the true
        # applied acceleration ("effort"): effort = effort_c @ u - effort_d @ s. Effort is the acceleration
        # itself when the axis is driven directly by the implied acceleration
        # (u - v)/tau when it's driven by a lagged velocity setpoint
        axis_taus = (tau_xy, tau_xy, tau_z)
        a_full = np.zeros((_STATE_DIM, _STATE_DIM))
        b_full = np.zeros((_STATE_DIM, _CONTROL_DIM))
        effort_c = np.zeros((_CONTROL_DIM, _CONTROL_DIM))
        effort_d = np.zeros((_CONTROL_DIM, _STATE_DIM))
        for axis, tau in enumerate(axis_taus):
            rows = slice(2 * axis, 2 * axis + 2)
            v_row = 2 * axis + 1
            # Exact zero-order-hold discretization of the continuous state space
            # where: dp/dt = v, dv/dt = (u - v)/tau.
            decay = np.exp(-dt / tau)
            pos_gain = tau * (1.0 - decay)
            a_block = np.array([[1.0, pos_gain], [0.0, decay]])
            b_block = np.array([[dt - pos_gain], [1.0 - decay]])
            effort_c[axis, axis] = 1.0 / tau
            effort_d[axis, v_row] = 1.0 / tau

            a_full[rows, rows] = a_block
            b_full[rows, axis:axis + 1] = b_block

        stage_weights = np.array([position_weight, velocity_weight] * 3)
        terminal_weights = np.array([terminal_position_weight, terminal_velocity_weight] * 3)
        acc_bounds = np.array([max_acc_xy_box, max_acc_xy_box, max_acc_z])

        s = cp.Variable((_STATE_DIM, n + 1))
        u = cp.Variable((_CONTROL_DIM, n))

        s0 = cp.Parameter(_STATE_DIM)
        u_prev = cp.Parameter(_CONTROL_DIM)
        ref = cp.Parameter((_STATE_DIM, n + 1))

        constraints = [s[:, 0] == s0]
        efforts = []
        for k in range(n):
            constraints.append(s[:, k + 1] == a_full @ s[:, k] + b_full @ u[:, k])
            effort_k = effort_c @ u[:, k] - effort_d @ s[:, k]
            efforts.append(effort_k)
            constraints.append(cp.abs(effort_k) <= acc_bounds)
            # Velocity components (vx, vy, vz) are at indices 1, 3, 5.
            constraints.append(cp.abs(s[1, k + 1]) <= max_speed_xy_box)
            constraints.append(cp.abs(s[3, k + 1]) <= max_speed_xy_box)
            constraints.append(cp.abs(s[5, k + 1]) <= max_speed_z)

        cost = 0
        for k in range(1, n + 1):
            error = s[:, k] - ref[:, k]
            weights = stage_weights if k < n else terminal_weights
            cost += cp.sum(cp.multiply(weights, cp.square(error)))

        previous_effort = effort_c @ u_prev - effort_d @ s0
        for k in range(n):
            cost += control_weight * cp.sum_squares(efforts[k])
            cost += control_rate_weight * cp.sum_squares(efforts[k] - previous_effort)
            previous_effort = efforts[k]

        problem = cp.Problem(cp.Minimize(cost), constraints)
        if not problem.is_dpp():
            raise RuntimeError("Trajectory MPC problem is not DPP-compliant; cannot warm-start efficiently")

        self._s = s
        self._u = u
        self._s0 = s0
        self._u_prev = u_prev
        self._ref = ref
        self._problem = problem

        self._last_command: Tuple[float, float, float] = (0.0, 0.0, 0.0)
        self._last_control: Tuple[float, float, float] = (0.0, 0.0, 0.0)

    @property
    def horizon_steps(self) -> int:
        """Number of steps in the prediction horizon."""
        return self._n

    @property
    def dt(self) -> float:
        """Duration, in seconds, of each step of the prediction horizon."""
        return self._dt

    def solve(
        self,
        position: Tuple[float, float, float],
        velocity: Tuple[float, float, float],
        reference_states: np.ndarray,
    ) -> Tuple[float, float, float]:
        """
        Solves the MPC for the current measured state and reference, returning the velocity
        command to apply for the next step.

        Args:
            position: Current measured position (x, y, z).
            velocity: Current measured velocity (vx, vy, vz).
            reference_states: Array of shape (6, horizon_steps + 1), reference state
                [px, vx, py, vy, pz, vz] at each step of the horizon (column 0 is "now",
                unused in the cost but required for consistency).

        Returns:
            The velocity command (vx, vy, vz) to send to the mobility handler for the next step.
            The output is the velocity setpoint itself - the value the lower-level controller will chase - since that's what the
            mobility handler's `tau`-driven tracking expects as a `SET_SPEED` command.
        """
        px, py, pz = position
        vx, vy, vz = velocity

        self._s0.value = np.array([px, vx, py, vy, pz, vz])
        self._u_prev.value = np.array(self._last_control)
        self._ref.value = reference_states

        self._problem.solve(solver=cp.OSQP, warm_start=True)

        if self._problem.status not in (cp.OPTIMAL, cp.OPTIMAL_INACCURATE):
            self._logger.warning(
                f"Trajectory MPC solve did not converge (status={self._problem.status}); "
                "holding last commanded velocity"
            )
            return self._last_command

        u0 = self._u.value[:, 0]
        command = tuple(
            float(u0[axis])
            for axis in range(3)
        )

        self._last_command = command
        self._last_control = tuple(self._u.value[:, 0])

        return command
