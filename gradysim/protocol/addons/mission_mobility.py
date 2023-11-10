from dataclasses import dataclass
from typing import List, Optional

from gradysim.protocol.addons.dispatcher import create_dispatcher, DispatchReturn
from gradysim.protocol.interface import IProtocol
from gradysim.protocol.messages.mobility import GotoCoordsMobilityCommand
from gradysim.protocol.messages.telemetry import Telemetry
from gradysim.protocol.position import Position, squared_distance


@dataclass
class MissionMobilityConfiguration:
    speed: float = 5
    """Speed in m/s the node will travel at during the mission"""

    loop_mission: bool = False
    """
    Loops the mission. If false the node will stop at the last position in the mission. If True the node will travel
    the mission backwards after reaching the last position and restart it after reaching the first position.
    """

    tolerance: float = 0.5
    """
    If the node is within this distance of a waypoint it is considered to have reached it.
    """


class MissionMobilityAddon:
    def __init__(self,
                 protocol: IProtocol,
                 configuration: MissionMobilityConfiguration = MissionMobilityConfiguration()):
        self._dispatcher = create_dispatcher(protocol)
        self._instance = protocol
        self._config = configuration

    _current_mission: Optional[List[Position]] = None
    _is_reversed: bool = False
    _is_idle: bool = True
    _current_waypoint: Optional[int] = None

    def _initialize_telemetry_handling(self) -> None:
        def telemetry_handler(_instance: IProtocol, telemetry: Telemetry) -> DispatchReturn:
            if self._current_mission is None:
                return DispatchReturn.CONTINUE

            if self._has_reached_target(telemetry.current_position):
                self._progress_mission()

    def _has_reached_target(self, current_position: Position):
        if self._current_waypoint is None:
            return False

        target_position = self._current_mission[self._current_waypoint]
        return squared_distance(current_position, target_position) <= self._config.tolerance ** 2

    def _progress_mission(self):
        if self._current_waypoint is None:
            return

        if self._is_reversed:
            if self._current_waypoint == 0:
                self._is_reversed = False
                self._progress_mission()
                return
            else:
                self._current_waypoint -= 1
        else:
            if self._current_waypoint == len(self._current_mission) - 1:
                if self._config.loop_mission:
                    self._is_reversed = True
                    self._progress_mission()
                    return
                else:
                    self._is_idle = True
                    return
            else:
                self._current_waypoint += 1

        mobility_command = GotoCoordsMobilityCommand(*self._current_mission[self._current_waypoint])
        self._instance.provider.send_mobility_command(mobility_command)

    def start_mission(self, mission: List[Position]) -> None:
        """
        Starts a mission, the node will travel to each position in the list in order and stop at the last position,
        unless the loop_mission option is set to True, in which case the node will travel the mission backwards after
        reaching the last position and restart it after reaching the first position.

        Args:
            mission: Sequence of positions the node will follow.
        """
        self._current_mission = mission
        self._is_reversed = False
        self._is_idle = False
        self._current_waypoint = 0

    def stop_mission(self) -> None:
        """
        Stops the current mission if there is one. If there is not, does nothing.
        """
        self._current_mission = None
        self._is_reversed = False
        self._is_idle = True
        self._current_waypoint = None

    @property
    def current_waypoint(self):
        return self._current_waypoint

    @property
    def is_reversed(self):
        return self._is_reversed