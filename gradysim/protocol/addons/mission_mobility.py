import enum
from dataclasses import dataclass
from typing import List, Optional

from gradysim.protocol.addons.dispatcher import create_dispatcher, DispatchReturn
from gradysim.protocol.interface import IProtocol
from gradysim.protocol.messages.mobility import GotoCoordsMobilityCommand
from gradysim.protocol.messages.telemetry import Telemetry
from gradysim.protocol.position import Position, squared_distance


class LoopMission(enum.Enum):
    NO = 1
    RESTART = 2
    REVERSE = 3


@dataclass
class MissionMobilityConfiguration:
    speed: float = 5
    """Speed in m/s the node will travel at during the mission"""

    loop_mission: LoopMission = LoopMission.NO
    """
    Configures how the mission should loop. If NO, the mission will end after reaching the final waypoint, this means
    that you would need to call start_mission again if you want it to follow another mission. If RESTART, the node will
    travel to the first waypoint of the mission and start the mission again. If REVERSE, will travel the mission in 
    reverse until the first waypoint, when it will start travelling the mission normally again.
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

        self._initialize_telemetry_handling()

    _current_mission: Optional[List[Position]] = None
    _is_reversed: bool = False
    _is_idle: bool = True
    _current_waypoint: Optional[int] = None

    def _initialize_telemetry_handling(self) -> None:
        def telemetry_handler(_instance: IProtocol, telemetry: Telemetry) -> DispatchReturn:
            if self._current_mission is None:
                return DispatchReturn.CONTINUE

            if self._has_reached_target(telemetry.current_position):
                self._progress_current_waypoint()
                self._travel_to_current_waypoint()

        self._dispatcher.register_handle_telemetry(telemetry_handler)

    def _has_reached_target(self, current_position: Position):
        if self._current_waypoint is None:
            return False

        target_position = self._current_mission[self._current_waypoint]
        return squared_distance(current_position, target_position) <= self._config.tolerance ** 2

    def _progress_current_waypoint(self):
        if self._current_mission is None:
            return

        if self._is_reversed:
            self._current_waypoint -= 1
        else:
            self._current_waypoint += 1

        if self._has_overran_bounds():
            if self._config.loop_mission == LoopMission.NO:
                self.stop_mission()
            elif self._config.loop_mission == LoopMission.RESTART:
                self._current_waypoint = 0
            elif self._config.loop_mission == LoopMission.REVERSE and self._is_reversed:
                self._current_waypoint = 0
                self._is_reversed = False
            elif self._config.loop_mission == LoopMission.REVERSE and not self._is_reversed:
                self._current_waypoint = len(self._current_mission) - 1
                self._is_reversed = True

    def _has_overran_bounds(self) -> bool:
        if self._current_mission is None:
            return False

        if self._is_reversed:
            return self._current_waypoint < 0
        else:
            return self._current_waypoint >= len(self._current_mission)

    def _travel_to_current_waypoint(self):
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
        self._travel_to_current_waypoint()

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