"""
Pure mathematical functions for velocity-based mobility.

This module contains stateless mathematical operations for:
- Acceleration limiting
- Velocity saturation
- Position integration

All functions operate on simple tuples and floats, making them
easy to test and reuse independently of the simulation framework.

Author: Laércio Lucchesi
Date: December 27, 2025
"""

import math
from typing import Optional, Tuple


def apply_acceleration_limits(
    v_current: Tuple[float, float, float],
    v_desired: Tuple[float, float, float],
    dt: float,
    max_acc_xy: float,
    max_acc_z: float
) -> Tuple[float, float, float]:
    """
    Limit velocity change based on acceleration constraints.
    
    Applies independent horizontal and vertical acceleration limits:
    - Horizontal: ||a_xy|| ≤ max_acc_xy
    - Vertical: |a_z| ≤ max_acc_z
    
    Args:
        v_current: Current velocity (vx, vy, vz) in m/s.
        v_desired: Desired velocity (vx, vy, vz) in m/s.
        dt: Time step in seconds.
        max_acc_xy: Maximum horizontal acceleration in m/s².
        max_acc_z: Maximum vertical acceleration in m/s².
    
    Returns:
        New velocity after applying acceleration limits.
    
    Example:
        >>> v_cur = (0.0, 0.0, 0.0)
        >>> v_des = (10.0, 10.0, 5.0)
        >>> v_new = apply_acceleration_limits(v_cur, v_des, 0.1, 2.0, 1.0)
        >>> # Horizontal component limited to 2.0 m/s² * 0.1 s = 0.2 m/s change
        >>> # Vertical component limited to 1.0 m/s² * 0.1 s = 0.1 m/s change
    """
    # Decompose into horizontal (xy) and vertical (z) components
    vx_cur, vy_cur, vz_cur = v_current
    vx_des, vy_des, vz_des = v_desired
    
    # Horizontal acceleration limiting
    dvx = vx_des - vx_cur
    dvy = vy_des - vy_cur
    dv_xy_norm = math.sqrt(dvx**2 + dvy**2)
    
    max_dv_xy = max_acc_xy * dt
    
    if dv_xy_norm > max_dv_xy:
        # Scale down to respect acceleration limit
        scale = max_dv_xy / dv_xy_norm
        dvx *= scale
        dvy *= scale
    
    vx_new = vx_cur + dvx
    vy_new = vy_cur + dvy
    
    # Vertical acceleration limiting
    dvz = vz_des - vz_cur
    max_dvz = max_acc_z * dt
    
    if abs(dvz) > max_dvz:
        dvz = math.copysign(max_dvz, dvz)
    
    vz_new = vz_cur + dvz
    
    return (vx_new, vy_new, vz_new)


def apply_velocity_tracking_first_order(
    v_current: Tuple[float, float, float],
    v_desired: Tuple[float, float, float],
    dt: float,
    max_acc_xy: float,
    max_acc_z: float,
    tau_xy: Optional[float],
    tau_z: Optional[float],
) -> Tuple[float, float, float]:
    """Track desired velocity using a 1st-order lag + acceleration saturation.

    This is a trajectory-level quadrotor-friendly model:

        a* = (v_des - v) / tau
        a  = sat(a*, max_acc)
        v+ = v + a * dt

    Horizontal saturation is applied on the norm of (ax, ay), while vertical
    saturation is applied on |az|.

    When tau_xy/tau_z are None, this function falls back to the existing
    "acceleration-limited step" behavior for that axis.
    """
    if dt <= 0:
        raise ValueError("dt must be > 0")
    if max_acc_xy < 0 or max_acc_z < 0:
        raise ValueError("max_acc must be >= 0")
    if tau_xy is not None and tau_xy <= 0:
        raise ValueError("tau_xy must be > 0 when provided")
    if tau_z is not None and tau_z <= 0:
        raise ValueError("tau_z must be > 0 when provided")

    vx_cur, vy_cur, vz_cur = v_current
    vx_des, vy_des, vz_des = v_desired

    # Horizontal (xy)
    if tau_xy is None:
        # Preserve legacy behavior for horizontal plane
        dvx = vx_des - vx_cur
        dvy = vy_des - vy_cur
        dv_xy_norm = math.sqrt(dvx**2 + dvy**2)
        max_dv_xy = max_acc_xy * dt
        if dv_xy_norm > max_dv_xy and dv_xy_norm > 0:
            scale = max_dv_xy / dv_xy_norm
            dvx *= scale
            dvy *= scale
        vx_new = vx_cur + dvx
        vy_new = vy_cur + dvy
    else:
        ax_des = (vx_des - vx_cur) / tau_xy
        ay_des = (vy_des - vy_cur) / tau_xy
        a_xy_norm = math.sqrt(ax_des**2 + ay_des**2)
        if a_xy_norm > max_acc_xy and a_xy_norm > 0:
            scale = max_acc_xy / a_xy_norm
            ax_des *= scale
            ay_des *= scale
        vx_new = vx_cur + ax_des * dt
        vy_new = vy_cur + ay_des * dt

    # Vertical (z)
    if tau_z is None:
        dvz = vz_des - vz_cur
        max_dvz = max_acc_z * dt
        if abs(dvz) > max_dvz:
            dvz = math.copysign(max_dvz, dvz)
        vz_new = vz_cur + dvz
    else:
        az_des = (vz_des - vz_cur) / tau_z
        if abs(az_des) > max_acc_z:
            az_des = math.copysign(max_acc_z, az_des)
        vz_new = vz_cur + az_des * dt

    return (vx_new, vy_new, vz_new)


def apply_velocity_limits(
    v: Tuple[float, float, float],
    max_speed_xy: float,
    max_speed_z: float
) -> Tuple[float, float, float]:
    """
    Apply velocity saturation constraints.
    
    Applies independent horizontal and vertical velocity limits:
    - Horizontal: ||v_xy|| ≤ max_speed_xy
    - Vertical: |v_z| ≤ max_speed_z
    
    Args:
        v: Velocity vector (vx, vy, vz) in m/s.
        max_speed_xy: Maximum horizontal speed in m/s.
        max_speed_z: Maximum vertical speed in m/s.
    
    Returns:
        Saturated velocity vector.
    
    Example:
        >>> v = (15.0, 15.0, 10.0)
        >>> v_sat = apply_velocity_limits(v, 10.0, 5.0)
        >>> # Horizontal norm is 21.21 m/s, scaled down to 10.0 m/s
        >>> # Vertical component clamped to 5.0 m/s
    """
    vx, vy, vz = v
    
    # Horizontal velocity saturation
    v_xy_norm = math.sqrt(vx**2 + vy**2)
    
    if v_xy_norm > max_speed_xy:
        scale = max_speed_xy / v_xy_norm
        vx *= scale
        vy *= scale
    
    # Vertical velocity saturation
    if abs(vz) > max_speed_z:
        vz = math.copysign(max_speed_z, vz)
    
    return (vx, vy, vz)


def integrate_position(
    position: Tuple[float, float, float],
    velocity: Tuple[float, float, float],
    dt: float
) -> Tuple[float, float, float]:
    """
    Update position using simple Euler integration.
    
    Implements: x_{k+1} = x_k + v_k * dt
    
    Args:
        position: Current position (x, y, z) in meters.
        velocity: Current velocity (vx, vy, vz) in m/s.
        dt: Time step in seconds.
    
    Returns:
        New position after integration step.
    
    Example:
        >>> pos = (0.0, 0.0, 0.0)
        >>> vel = (1.0, 2.0, 0.5)
        >>> new_pos = integrate_position(pos, vel, 0.1)
        >>> new_pos
        (0.1, 0.2, 0.05)
    """
    x, y, z = position
    vx, vy, vz = velocity
    
    return (
        x + vx * dt,
        y + vy * dt,
        z + vz * dt
    )
