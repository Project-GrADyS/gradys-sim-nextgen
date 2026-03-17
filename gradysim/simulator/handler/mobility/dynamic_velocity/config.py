"""
Configuration dataclass for the Dynamic Velocity Mobility Handler.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class DynamicVelocityMobilityConfiguration:
    """
    Configuration parameters for the Dynamic Velocity Mobility Handler.
    
    Attributes:
        update_rate: Time interval (in seconds) between mobility updates.
            Typical for trajectory-level quadrotor sims: 0.01–0.05 s.
        max_speed_xy: Maximum horizontal speed (m/s). Applied to the norm of (vx, vy).
            Typical: 3–15 m/s (depends heavily on vehicle and mission).
        max_speed_z: Maximum vertical speed (m/s). Applied to |vz|.
            Typical: 1–8 m/s.
        max_acc_xy: Maximum horizontal acceleration (m/s²). Applied to the norm of (ax, ay).
            Typical: 2–8 m/s².
        max_acc_z: Maximum vertical acceleration (m/s²). Applied to |az|.
            Typical: 2–10 m/s².
        tau_xy: Optional first-order time constant (seconds) for horizontal velocity tracking.
            When set, the model behaves like a 1st-order system + acceleration saturation:
                a* = (v_des - v) / tau_xy
            Typical: 0.3–0.8 s.
        tau_z: Optional first-order time constant (seconds) for vertical velocity tracking.
            Typical: 0.5–1.2 s.
        send_telemetry: If True, emit Telemetry messages after position updates.
        telemetry_decimation: Emit telemetry every N mobility updates (default: 1).
    """
    update_rate: float
    max_speed_xy: float
    max_speed_z: float
    max_acc_xy: float
    max_acc_z: float
    tau_xy: Optional[float] = None
    tau_z: Optional[float] = None
    send_telemetry: bool = True
    telemetry_decimation: int = 1
