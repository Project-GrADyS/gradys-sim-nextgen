import random
from typing import Tuple, Type, Callable

from simulator.messages.mobility import MobilityCommand, MobilityCommandType
from simulator.messages.telemetry import Telemetry
from simulator.position import Position, squared_distance
from simulator.protocols.interface import IProtocol


class RandomMobilityConfig:
    def __init__(self, x_range: Tuple[float, float] = (-50, 50),
                 y_range: Tuple[float, float] = (-50, 50),
                 z_range: Tuple[float, float] = (0, 50),
                 tolerance: float = 0.5):
        self.x_range = x_range
        self.y_range = y_range
        self.z_range = z_range
        self.tolerance = tolerance
        self.squared_tolerance = tolerance * tolerance


class RandomMobilityAddon:
    """
    Addon for random mobility. This addon will assist you in implementing random movement behaviour in your
    protocols
    """
    def __init__(self, protocol: IProtocol, config: RandomMobilityConfig = RandomMobilityConfig()):
        self.instance = protocol
        self.config = config

    def travel_to_random_waypoint(self) -> Position:
        """
        Issues a mobility command that makes the node travel to a randomly drawn position within
        the range specified in the configuration of this class.
        :return: Node's new destination
        """
        random_waypoint = (
            random.uniform(*self.config.x_range),
            random.uniform(*self.config.y_range),
            random.uniform(*self.config.z_range)
        )

        command = MobilityCommand(
            MobilityCommandType.GOTO_COORDS,
            *random_waypoint
        )

        self.instance.provider.send_mobility_command(command)
        return random_waypoint

    _current_target: Position
    _instance_handle_telemetry: Type[IProtocol.handle_telemetry]
    _trip_ongoing: bool

    def initiate_random_trip(self) -> None:
        """
        Initiates a random trip. This means this node will draw a random waypoing, travel to it and repeat
        this process until finish_random_trip is called.
        """
        self._current_target = self.travel_to_random_waypoint()

        self._instance_handle_telemetry = self.instance.handle_telemetry

        def patched_handle_telemetry(_instance: IProtocol, telemetry: Telemetry):
            if squared_distance(telemetry.current_position, self._current_target) <= self.config.squared_tolerance:
                self.travel_to_random_waypoint()

            self._instance_handle_telemetry(telemetry)

        self.instance.handle_telemetry = patched_handle_telemetry

        self._trip_ongoing = True

    def finish_random_trip(self) -> None:
        """
        Finishes an ongoing random trip
        """
        if self._trip_ongoing:
            self.instance.handle_telemetry = self._instance_handle_telemetry
            self._trip_ongoing = False

    @property
    def trip_ongoing(self):
        return self._trip_ongoing

    @property
    def current_target(self):
        return self._current_target
