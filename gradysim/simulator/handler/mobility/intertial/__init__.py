"""
GrADyS-SIM NG Velocity Mobility Handler

A velocity-driven mobility handler for the GrADyS-SIM NG simulator,
designed for distributed controllers that output velocity vectors.

Key features:
- Direct velocity control (no waypoints)
- Independent horizontal and vertical constraints
- Acceleration-limited velocity tracking
- Optional telemetry emission

Author: Laércio Lucchesi
Date: December 27, 2025
"""

from .config import InertialMobilityConfiguration
from .handler import InertialMobilityHandler
from .core import (
    apply_acceleration_limits,
    apply_velocity_limits,
    integrate_position
)

__version__ = "0.1.0"

__all__ = [
    "InertialMobilityConfiguration",
    "InertialMobilityHandler",
    "apply_acceleration_limits",
    "apply_velocity_limits",
    "integrate_position",
]
