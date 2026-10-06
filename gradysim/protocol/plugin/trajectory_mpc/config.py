"""
Configuration dataclass for the Trajectory MPC plugin.
"""

import math
from dataclasses import dataclass
from typing import Optional

from gradysim.simulator.handler.mobility.dynamic_velocity.config import DynamicVelocityMobilityConfiguration


@dataclass
class TrajectoryMPCConfiguration:
    """
    Configuration parameters for TrajectoryMPCPlugin

    """

    control_period: float
    """Time interval (in seconds) between MPC solves/replans. Should be higher than the
    mobility handler's own `update_rate` (same cascaded-loop-rate pattern real flight
    controllers use)."""

    horizon_steps: int
    """Number of steps in the MPC's prediction horizon."""

    max_speed_xy: float
    """Maximum horizontal speed (m/s), matching the mobility handler's configuration."""

    max_speed_z: float
    """Maximum vertical speed (m/s), matching the mobility handler's configuration."""

    max_acc_xy: float
    """Maximum horizontal acceleration (m/s^2), matching the mobility handler's configuration."""

    max_acc_z: float
    """Maximum vertical acceleration (m/s^2), matching the mobility handler's configuration."""

    tau_xy: float
    """First-order time constant (seconds) for horizontal velocity tracking, matching
    the mobility handler's configuration."""

    tau_z: float
    """First-order time constant (seconds) for vertical velocity tracking, matching the
    mobility handler's configuration. Same effect as `tau_xy`, applied to the z axis."""

    position_weight: float = 10.0
    """Cost weight on position tracking error at each step of the horizon."""

    velocity_weight: float = 1.0
    """Cost weight on velocity tracking error at each step of the horizon."""

    control_weight: float = 0.05
    """Cost weight on control (acceleration) effort at each step of the horizon."""

    control_rate_weight: float = 0.05
    """Cost weight on the change in control between consecutive steps, penalizing jerky plans."""

    terminal_position_weight: float = 20.0
    """Cost weight on position tracking error at the end of the horizon."""

    terminal_velocity_weight: float = 2.0
    """Cost weight on velocity tracking error at the end of the horizon."""

    tolerance: float = 1.0
    """Distance (in meters) from the final waypoint within which the trajectory is considered finished."""

    @property
    def max_speed_xy_box(self) -> float:
        """Per-axis horizontal speed bound actually enforced by the QP ."""
        return self.max_speed_xy / math.sqrt(2)

    @property
    def max_acc_xy_box(self) -> float:
        """Per-axis horizontal acceleration bound actually enforced by the QP."""
        return self.max_acc_xy / math.sqrt(2)

    @classmethod
    def from_dynamic_velocity_config(
        cls,
        dynamic_velocity_config: DynamicVelocityMobilityConfiguration,
        control_period: float,
        horizon_steps: int,
        **overrides,
    ) -> "TrajectoryMPCConfiguration":
        """
        Builds a TrajectoryMPCConfiguration whose speed/acceleration limits are copied directly
        from the Dynamic Velocity Mobility Configuration], guaranteeing the MPC never plans something the mobility handler can't execute.

        Args:
            dynamic_velocity_config: Configuration of the mobility handler the MPC's plan will be sent to.
            control_period: Time interval (in seconds) between MPC solves/replans (should be bigger than the lower control loop period).
            horizon_steps: Number of steps in the MPC's prediction horizon.
            **overrides: Any other TrajectoryMPCConfiguration field (e.g. cost weights, tolerance)
                to override from its default.

        Returns:
            A new TrajectoryMPCConfiguration.
        """
        return cls(
            control_period=control_period,
            horizon_steps=horizon_steps,
            max_speed_xy=dynamic_velocity_config.max_speed_xy,
            max_speed_z=dynamic_velocity_config.max_speed_z,
            max_acc_xy=dynamic_velocity_config.max_acc_xy,
            max_acc_z=dynamic_velocity_config.max_acc_z,
            tau_xy=dynamic_velocity_config.tau_xy,
            tau_z=dynamic_velocity_config.tau_z,
            **overrides,
        )
