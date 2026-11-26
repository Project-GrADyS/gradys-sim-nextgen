"""
ORCA Collision Avoidance plugin for GrADyS-SIM NextGen.

Lets a protocol perform reciprocal (ORCA) collision avoidance against nearby UAVs running the
same plugin, discovering them via a small self-broadcast heartbeat (position/velocity/ID).
Combine it with
[TrajectoryMPCPlugin][gradysim.protocol.plugin.trajectory_mpc.TrajectoryMPCPlugin] (or any other
source of a goal velocity) in a cascade: feed your protocol's own desired velocity in via
`set_goal_velocity`, and switch to `avoidance_velocity` whenever `is_colliding` is True.

Usage:
    config = OrcaAvoidanceConfiguration(max_speed=8.0, inflation_radius=3.0)
    avoidance = OrcaAvoidancePlugin(self, config)

    # Each control tick:
    avoidance.set_goal_velocity(*my_goal_velocity)
    if avoidance.is_colliding:
        vx, vy, vz = avoidance.avoidance_velocity
    else:
        vx, vy, vz = my_goal_velocity
    self.provider.send_mobility_command(SetVelocityMobilityCommand(vx, vy, vz))
"""

from .config import OrcaAvoidanceConfiguration
from .heartbeat import HeartbeatMessage
from .plugin import OrcaAvoidancePlugin, OrcaAvoidancePluginException

__all__ = [
    "OrcaAvoidancePlugin",
    "OrcaAvoidancePluginException",
    "OrcaAvoidanceConfiguration",
    "HeartbeatMessage",
]
