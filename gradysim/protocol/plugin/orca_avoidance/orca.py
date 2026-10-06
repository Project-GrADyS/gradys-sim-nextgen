"""
Core ORCA (Optimal Reciprocal Collision Avoidance) math: per-neighbor half-plane construction in
full 3D velocity space, and the QP that turns those half-planes plus a speed bound into a single
avoidance velocity.

Follows the standard reciprocal velocity-obstacle derivation (van den Berg et al., "Reciprocal
n-Body Collision Avoidance", 2011), generalized from the well-known 2D formulas (as implemented in
e.g. the RVO2 library) to 3D.
"""

from dataclasses import dataclass
from typing import List, Sequence, Tuple

import cvxpy as cp
import numpy as np

from gradysim.protocol.position import Position

_EPSILON = 1e-9
_SLACK_PENALTY = 1e4


@dataclass
class _NeighborCorrection:
    normal: np.ndarray
    """Unit vector pointing from the relative velocity towards the nearest point on the (possibly
    truncated) velocity obstacle boundary, i.e. the direction that resolves the conflict."""

    u: np.ndarray
    """Vector from the current relative velocity to that nearest boundary point. Always parallel
    to normal; its length is the distance to the boundary."""

    on_collision_course: bool
    """Whether the current relative velocity lies inside the velocity obstacle."""


def _arbitrary_perpendicular(vector: np.ndarray) -> np.ndarray:
    """Returns an arbitrary unit vector perpendicular to vector (which must be nonzero). Used
    for degenerate cases (a perfectly head-on approach) where the geometry doesn't determine
    a unique correction direction."""
    axis = np.array([1.0, 0.0, 0.0])
    if abs(float(vector @ axis)) > 0.9 * np.linalg.norm(vector):
        axis = np.array([0.0, 1.0, 0.0])
    perpendicular = np.cross(vector, axis)
    return perpendicular / np.linalg.norm(perpendicular)


def _neighbor_correction(
    relative_position: np.ndarray,
    relative_velocity: np.ndarray,
    combined_radius: float,
    horizon: float,
    dt: float,
) -> _NeighborCorrection:
    """
    Computes the ORCA correction for a single neighbor, given this agent's position/velocity
    relative to it.

    Args:
        relative_position: Neighbor's position minus this agent's position.
        relative_velocity: This agent's velocity minus the neighbor's velocity.
        combined_radius: Minimum separation to maintain from this neighbor.
        horizon: Time horizon (tau) for the velocity obstacle truncation.
        dt: Control step used in place of horizon for the degenerate already-overlapping case.            
    """
    p = relative_position
    v = relative_velocity
    r = combined_radius
    dist_sq = float(p @ p)
    combined_radius_sq = r * r

    if dist_sq > combined_radius_sq:
        w = v - p / horizon # relative velocity to the center of the collision cone
                            # difference between the current relative velocity and the worst case scenario,
                            # going straight to the center. 
        w_length_sq = float(w @ w)
        dot_product_1 = float(w @ p)

        if dot_product_1 < 0.0 and dot_product_1 ** 2 > combined_radius_sq * w_length_sq:
            # dot_product_1 < 0 
                # (v - p / horizon) @ p < 0
                # v @ p < ||p||**2 / horizon
                # (v @ p)/||p|| < ||p|| / horizon
                # Projection of the relative velocity onto the relative position is less than the distance to the neighbor divided by the time horizon
                # forward speed toward the neighbor is less than the speed needed to hit their center in exactly hoziron seconds.
            # dot_product_1 ** 2 > combined_radius_sq * w_length_sq
                # (w @ p)**2 > r**2 * ||w||**2
                # ||w||**2 * ||p||**2 * cos(alpha)**2 > r**2 * ||w||**2  (where alpha is the angle between w and p)
                # ||p||**2 * cos(alpha)**2 > r**2
                # cos(alpha)**2 > r**2 / ||p||**2
                # Geometrically, the cone's half-angle (theta) is defined by sin(theta) = r / ||p||
                # So, r**2 / ||p||**2 is exactly sin(theta)**2
                # The condition becomes: cos(alpha)**2 > sin(theta)**2
                # This proves your deviation angle (alpha) is narrower than the obstacle's physical width angle (theta).
                # In behavior: You are aimed squarely at the center, trapped within the direct shadow of their radius (head-on collision).

            if w_length_sq > _EPSILON:
                w_length = np.sqrt(w_length_sq)
                unit_w = w / w_length
            else:
                w_length = 0.0
                unit_w = _arbitrary_perpendicular(p)
            normal = unit_w
            u = (r / horizon - w_length) * unit_w
        else:
            # Project onto the lateral cone surface. Decompose the relative velocity into
            # components parallel/perpendicular to the relative position, then find the nearest
            # point on the cone (apex at the origin, axis along p, half-angle theta) directly -
            # this is the 3D generalization of the 2D "tangent line" projection.
            leg = np.sqrt(dist_sq - combined_radius_sq)
            p_length = np.sqrt(dist_sq)
            p_hat = p / p_length
            sin_theta = r / p_length
            cos_theta = leg / p_length

            a = float(v @ p_hat)
            v_perp = v - a * p_hat
            rho = float(np.linalg.norm(v_perp))
            e_hat = v_perp / rho if rho > _EPSILON else _arbitrary_perpendicular(p_hat)

            direction = cos_theta * p_hat + sin_theta * e_hat
            normal = -sin_theta * p_hat + cos_theta * e_hat
            t_star = a * cos_theta + rho * sin_theta
            u = t_star * direction - v
    else:
        # Already overlapping: push apart as fast as the next control step allows.
        # Control step is smaller than the time horizon, so it pushes for a more aggressive maneuver
        w = v - p / dt
        w_length = float(np.linalg.norm(w))
        if w_length > _EPSILON:
            unit_w = w / w_length
        else:
            unit_w = _arbitrary_perpendicular(p) if dist_sq > _EPSILON else np.array([1.0, 0.0, 0.0])
        normal = unit_w
        u = (r / dt - w_length) * unit_w
        return _NeighborCorrection(normal=normal, u=u, on_collision_course=True)

    on_collision_course = float(u @ normal) > 0.0
    return _NeighborCorrection(normal=normal, u=u, on_collision_course=on_collision_course)


def is_on_collision_course(
    self_position: Position,
    self_velocity: Position,
    neighbor_position: Position,
    neighbor_velocity: Position,
    combined_radius: float,
    horizon: float,
    dt: float,
) -> bool:
    """Whether neighbor is on a collision course with self within horizon seconds, under a
    constant-velocity extrapolation of both agents' current velocities."""
    p = np.array(neighbor_position) - np.array(self_position)
    v = np.array(self_velocity) - np.array(neighbor_velocity)
    return _neighbor_correction(p, v, combined_radius, horizon, dt).on_collision_course


def solve(
    preferred_velocity: Position,
    self_position: Position,
    self_velocity: Position,
    neighbors: Sequence[Tuple[Position, Position]],
    combined_radius: float,
    max_speed_box: float,
    horizon: float,
    dt: float,
) -> Tuple[float, float, float]:
    """
    Solves the ORCA QP: the velocity closest to preferred_velocity that respects every
    neighbor's half-plane and the box-approximated speed bound.

    Args:
        preferred_velocity: The velocity to steer towards absent any conflict.
        self_position: This agent's current position.
        self_velocity: This agent's current velocity.
        neighbors: (position, velocity) of each neighbor to avoid, already filtered by the caller.
        combined_radius: Minimum separation to maintain from any neighbor.
        max_speed_box: Per-axis speed bound (inscribed-box approximation of the true speed cap).
        horizon: Time horizon (tau) for the velocity obstacle truncation.
        dt: Control step, used for the degenerate already-overlapping case.

    Returns:
        The collision-free velocity (vx, vy, vz) closest to preferred_velocity.
    """
    self_pos = np.array(self_position)
    self_vel = np.array(self_velocity)
    pref = np.array(preferred_velocity)

    planes: List[Tuple[np.ndarray, np.ndarray]] = []
    for neighbor_position, neighbor_velocity in neighbors:
        p = np.array(neighbor_position) - self_pos
        v = self_vel - np.array(neighbor_velocity)
        correction = _neighbor_correction(p, v, combined_radius, horizon, dt)
        point = self_vel + 0.5 * correction.u
        planes.append((correction.normal, point))

    velocity = cp.Variable(3)
    constraints = [cp.abs(velocity) <= max_speed_box]
    for normal, point in planes:
        constraints.append(normal @ (velocity - point) >= 0)

    problem = cp.Problem(cp.Minimize(cp.sum_squares(velocity - pref)), constraints)
    problem.solve(solver=cp.OSQP)

    if problem.status in (cp.OPTIMAL, cp.OPTIMAL_INACCURATE):
        return tuple(float(x) for x in velocity.value)

    # Infeasible - fall back to a slack-relaxed solve that's always
    # feasible: penalize violating a plane instead of forbidding it
    # outright, giving a best-effort minimal-violation velocity.
    slacks = cp.Variable(len(planes), nonneg=True)
    relaxed_constraints = [cp.abs(velocity) <= max_speed_box]
    for (normal, point), slack in zip(planes, slacks):
        relaxed_constraints.append(normal @ (velocity - point) >= -slack)

    relaxed_problem = cp.Problem(
        cp.Minimize(cp.sum_squares(velocity - pref) + _SLACK_PENALTY * cp.sum(slacks)),
        relaxed_constraints,
    )
    relaxed_problem.solve(solver=cp.OSQP)

    if relaxed_problem.status in (cp.OPTIMAL, cp.OPTIMAL_INACCURATE):
        return tuple(float(x) for x in velocity.value)

    # Hold position rather than propagate a bad velocity if the solver still fails.
    return (0.0, 0.0, 0.0)
