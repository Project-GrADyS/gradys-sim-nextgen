"""
Configuration dataclass for the ORCA Avoidance plugin.
"""

import math
from dataclasses import dataclass
from typing import Optional

from gradysim.simulator.handler.mobility.dynamic_velocity.config import DynamicVelocityMobilityConfiguration


@dataclass
class OrcaAvoidanceConfiguration:
    """
    Configuration parameters for OrcaAvoidancePlugin.
    """

    max_speed: float
    """Total max speed bound (m/s) enforced on the ORCA-computed velocity. Approximated as a 
    cube (max_speed / sqrt(3)) per axis."""

    inflation_radius: float
    """Minimum separation (in meters) to maintain from any neighbor. Double the inflation radius"""

    time_horizon: float = 2.0
    """ORCA's tau: how far ahead (in seconds) a neighbor's constant-velocity extrapolation is
    projected when deciding whether it's on a collision course and when building its avoidance
    half-plane."""

    heartbeat_period: float = 0.5
    """Time interval (in seconds) between broadcasts of this UAV's own position/velocity/ID."""

    orca_period: float = 0.5
    """Time interval (in seconds) between recomputations of the avoidance velocity."""

    neighbor_timeout: Optional[float] = None
    """Time (in seconds) without a heartbeat from a neighbor before it's dropped from tracking.
    If None, resolved as 4 * heartbeat_period"""

    max_neighbors: Optional[int] = None
    """Cap on the number of nearest neighbors included in the avoidance solve, to bound compute
    cost regardless of swarm size. None means all neighbors."""

    neighbor_distance: Optional[float] = None
    """Ignore neighbors farther than this distance (in meters) when building the avoidance solve.
    None means no cutoff."""

    @property
    def max_speed_box(self) -> float:
        """Per-axis speed bound actually enforced by the QP."""
        return self.max_speed / math.sqrt(3)

    @property
    def effective_neighbor_timeout(self) -> float:
        """The neighbor timeout actually used: neighbor_timeout if set, otherwise
        4 * heartbeat_period."""
        if self.neighbor_timeout is not None:
            return self.neighbor_timeout
        return 4 * self.heartbeat_period

    @classmethod
    def from_dynamic_velocity_config(
        cls,
        dynamic_velocity_config: DynamicVelocityMobilityConfiguration,
        inflation_radius: float,
        **overrides,
    ) -> "OrcaAvoidanceConfiguration":
        """
        Builds an OrcaAvoidanceConfiguration whose speed bound is the largest sphere that still
        fits inside the Dynamic Velocity Mobility Configuration's speed, guaranteeing the ORCA
        solve never requests something the mobility handler can't execute.

        Args:
            dynamic_velocity_config: Configuration of the mobility handler the avoidance velocity
                will be sent to.
            inflation_radius: Minimum separation (in meters) to maintain from any neighbor.
            **overrides: Any other OrcaAvoidanceConfiguration field (e.g. time_horizon,
                orca_period) to override from its default.

        Returns:
            A new OrcaAvoidanceConfiguration.
        """
        return cls(
            max_speed=min(dynamic_velocity_config.max_speed_xy, dynamic_velocity_config.max_speed_z),
            inflation_radius=inflation_radius,
            **overrides,
        )
