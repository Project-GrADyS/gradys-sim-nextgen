"""
A common use case of network simulations is to simulate a network of mobile nodes whose mobility is random. This addon
provides a simple way to implement random mobility in your protocol.
"""
import logging
import random
import types
from dataclasses import dataclass
from typing import Tuple, Type, Optional

from gradys.simulator.log import SIMULATION_LOGGER
from gradys.protocol.messages.mobility import MobilityCommand, MobilityCommandType
from gradys.protocol.messages.telemetry import Telemetry
from gradys.simulator.position import Position, squared_distance
from gradys.protocol.interface import IProtocol


@dataclass
class RandomMobilityConfig:
    """
    Configuration class for the [RandomMobilityAddon][gradys.protocol.addons.random_mobility.RandomMobilityAddon] class.
    """

    x_range: Tuple[float, float] = (-50, 50)
    """Random waypoints will be drawn from this range for the x coordinate"""

    y_range: Tuple[float, float] = (-50, 50)
    """Random waypoints will be drawn from this range for the y coordinate"""

    z_range: Tuple[float, float] = (0, 50)
    """Random waypoints will be drawn from this range for the z coordinate"""

    tolerance: float = 1
    """
    Tolerance in meters for considering a waypoint as reached. When the node is within this distance from the
    waypoint, it will be considered as reached and a new waypoint will be drawn, if a random trip is ongoing.
    """


class RandomMobilityAddon:
    """
    Addon for random mobility. This addon will assist you in implementing random movement behaviour in your
    protocol.

    This addon should be initialized by your protocol. To use it you should call the
    [initiate_random_trip][gradys.protocol.addons.random_mobility.RandomMobilityAddon.initiate_random_trip] method to start
    a random trip. This method will make the node travel to a random waypoint and then draw a new waypoint when the
    node reaches it. This process will repeat until you call the
    [finish_random_trip][gradys.protocol.addons.random_mobility.RandomMobilityAddon.finish_random_trip] method.

    If you only want to make the node travel to a random waypoint once, you can use the
    [travel_to_random_waypoint][gradys.protocol.addons.random_mobility.RandomMobilityAddon.travel_to_random_waypoint] method.
    """
    def __init__(self, protocol: IProtocol, config: RandomMobilityConfig = RandomMobilityConfig()):
        """
        Initializes the addon

        Args:
            protocol: The protocol instance to which this addon will be attached
            config: Configuration for the addon, if not specified, the default configuration will be used
        """
        self._instance = protocol
        self._config = config
        self._logger = logging.getLogger(SIMULATION_LOGGER)

    def travel_to_random_waypoint(self) -> Position:
        """
        Issues a mobility command that makes the node travel to a randomly drawn position within
        the range specified in the configuration of this class.

        Returns:
            Node's new destination
        """
        random_waypoint = (
            random.uniform(*self._config.x_range),
            random.uniform(*self._config.y_range),
            random.uniform(*self._config.z_range)
        )

        command = MobilityCommand(
            MobilityCommandType.GOTO_COORDS,
            *random_waypoint
        )

        self._logger.info(f"RandomMobilityAddon: traveling to waypoint {random_waypoint}")

        self._instance.provider.send_mobility_command(command)
        return random_waypoint

    _current_target: Optional[Position]
    _instance_handle_telemetry: Type[IProtocol.handle_telemetry]
    _trip_ongoing: bool

    def initiate_random_trip(self) -> None:
        """
        Initiates a random trip. This means this node will draw a random waypoint, travel to it and repeat
        this process until finish_random_trip is called.
        """
        self._logger.info("RandomMobilityAddon: Initiating a random trip")
        self._current_target = self.travel_to_random_waypoint()

        self._instance_handle_telemetry = self._instance.handle_telemetry

        def patched_handle_telemetry(instance: IProtocol, telemetry: Telemetry):
            if squared_distance(telemetry.current_position, self._current_target) <= \
                    (self._config.tolerance * self._config.tolerance):
                self._current_target = self.travel_to_random_waypoint()

            self._instance_handle_telemetry(telemetry)

        self._instance.handle_telemetry = types.MethodType(patched_handle_telemetry, self._instance)

        self._trip_ongoing = True

    def finish_random_trip(self) -> None:
        """
        Finishes an ongoing random trip. If no trip is ongoing, this method does nothing.
        """
        self._logger.info("RandomMobilityAddon: Finishing a random trip")
        if self._trip_ongoing:
            self._instance.handle_telemetry = self._instance_handle_telemetry
            self._trip_ongoing = False

    @property
    def trip_ongoing(self):
        """
        Returns whether a random trip is ongoing or not
        Returns:
            True if a random trip is ongoing, False otherwise
        """
        return self._trip_ongoing

    @property
    def current_target(self) -> Optional[Position]:
        """
        Returns the position the node is currently traveling to, or None if it isn't traveling anywhere.

        Returns:
            The position the node is currently traveling to, or None if it isn't traveling anywhere.
        """
        return self._current_target
