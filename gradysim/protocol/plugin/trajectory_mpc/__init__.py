"""
Trajectory MPC plugin for GrADyS-SIM NextGen.

Lets a protocol hand over a time-parameterized trajectory (positions and the times they should
be reached) and have a Model Predictive Controller compute the velocity commands needed to track
it, given the known, bounded dynamics of
[DynamicVelocityMobilityHandler][gradysim.simulator.handler.mobility.dynamic_velocity.handler.DynamicVelocityMobilityHandler].

Usage:
    config = TrajectoryMPCConfiguration.from_dynamic_velocity_config(
        dynamic_velocity_config,
        control_period=0.1,
        horizon_steps=15,
    )
    trajectory_plugin = TrajectoryMPCPlugin(self, config)

    reference = PiecewiseLinearReference([
        TrajectoryPoint((10, 0, 0), 5.0),
        TrajectoryPoint((10, 10, 0), 10.0),
        TrajectoryPoint((0, 0, 0), 20.0),
    ])
    trajectory_plugin.start_trajectory(reference)
"""

from .config import TrajectoryMPCConfiguration
from .plugin import TrajectoryMPCPlugin, TrajectoryMPCPluginException
from .reference import ITrajectoryReference, PiecewiseLinearReference, TrajectoryPoint

__all__ = [
    "TrajectoryMPCPlugin",
    "TrajectoryMPCPluginException",
    "TrajectoryMPCConfiguration",
    "TrajectoryPoint",
    "ITrajectoryReference",
    "PiecewiseLinearReference",
]
