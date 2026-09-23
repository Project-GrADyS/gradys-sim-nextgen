"""
Pure functions/classes for turning a list of timed waypoints into a continuous
position/velocity reference. Just for testing porposes, in real-time applications
the reference should be generated on-the-fly by a separate process
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Tuple

from gradysim.protocol.position import Position


@dataclass
class TrajectoryPoint:
    """
    A single waypoint in a trajectory: a position to be reached at a given time.
    """

    position: Position
    """Position (x, y, z) of the waypoint, in meters in the global reference frame."""

    time: float
    """Time at which the waypoint should be reached, in seconds since the trajectory started."""


class ITrajectoryReference(ABC):
    """
    Interface for a time-parameterized position/velocity reference that TrajectoryMPCPlugin
    tracks. Implement this to feed the MPC a reference other than a piecewise-linear
    interpolation of waypoints.
    """

    @property
    @abstractmethod
    def final_time(self) -> float:
        """Time, in seconds since the trajectory started, at which the reference ends."""

    @property
    @abstractmethod
    def final_position(self) -> Position:
        """Position the reference holds at and after `final_time`."""

    @abstractmethod
    def evaluate(self, t: float) -> Tuple[Position, Position]:
        """
        Evaluates the reference at time t.

        Args:
            t: Time in seconds since the trajectory started.

        Returns:
            A tuple (position_ref, velocity_ref), each a (x, y, z) tuple.
        """


class PiecewiseLinearReference(ITrajectoryReference):
    """
    Time-parameterized reference built from a sequence of TrajectoryPoints

    Between two consecutive waypoints the reference position interpolates linearly and the
    reference velocity is the constant slope of that segment. Before the first waypoint and
    after the last one, the reference holds position with zero velocity.
    """

    def __init__(self, trajectory: List[TrajectoryPoint]):
        if len(trajectory) == 0:
            raise ValueError("Trajectory must contain at least one point")

        times = [point.time for point in trajectory]
        if any(t2 <= t1 for t1, t2 in zip(times, times[1:])):
            raise ValueError("Trajectory times must be strictly increasing")

        self._trajectory = trajectory

    @property
    def final_time(self) -> float:
        """Time, in seconds since the trajectory started, of the last waypoint."""
        return self._trajectory[-1].time

    @property
    def final_position(self) -> Position:
        """Position of the last waypoint."""
        return self._trajectory[-1].position

    def evaluate(self, t: float) -> Tuple[Position, Position]:
        """
        Evaluates the reference at time t.

        Args:
            t: Time in seconds since the trajectory started.

        Returns:
            A tuple (position_ref, velocity_ref), each a (x, y, z) tuple.
        """
        trajectory = self._trajectory

        if t <= trajectory[0].time:
            return trajectory[0].position, (0.0, 0.0, 0.0)

        if t >= trajectory[-1].time:
            return trajectory[-1].position, (0.0, 0.0, 0.0)

        # Find the segment [i, i+1] such that trajectory[i].time <= t < trajectory[i+1].time
        i = 0
        while trajectory[i + 1].time <= t:
            i += 1

        start, end = trajectory[i], trajectory[i + 1]
        duration = end.time - start.time
        alpha = (t - start.time) / duration

        position = tuple(
            p0 + (p1 - p0) * alpha
            for p0, p1 in zip(start.position, end.position)
        )
        velocity = tuple(
            (p1 - p0) / duration
            for p0, p1 in zip(start.position, end.position)
        )

        return position, velocity
