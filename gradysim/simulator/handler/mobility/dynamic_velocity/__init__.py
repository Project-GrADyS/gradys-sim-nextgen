"""
GrADyS-SIM NG Dynamic Velocity Mobility Handler

A dynamic velocity mobility handler for the GrADyS-SIM NG simulator,
designed for distributed controllers that output velocity vectors.

Key features:

- Direct velocity control (no waypoints)
- Independent horizontal and vertical constraints
- Acceleration-limited velocity tracking
- Optional telemetry emission
"""

from .config import DynamicVelocityMobilityConfiguration
from .handler import DynamicVelocityMobilityHandler
from .core import (
    apply_acceleration_limits,
    apply_velocity_limits,
    integrate_position
)

__version__ = "0.1.0"

__all__ = [
    "DynamicVelocityMobilityConfiguration",
    "DynamicVelocityMobilityHandler",
    "apply_acceleration_limits",
    "apply_velocity_limits",
    "integrate_position",
]
