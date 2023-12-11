import enum
import logging
from dataclasses import dataclass
from typing import List, Optional

from gradysim.protocol.plugin.dispatcher import create_dispatcher, DispatchReturn
from gradysim.protocol.interface import IProtocol
from gradysim.protocol.messages.mobility import GotoCoordsMobilityCommand, SetSpeedMobilityCommand
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


class MissionMobilityPluginException(Exception):
    pass


class MissionMobilityPlugin:
    """
    Use this plugin if you want your node to follow a fixed list of positions, or waypoints. The waypoints will be
    followed in order after they are received by the start_mission method. You can stop the mission
    at any time using stop_mission. The current_waypoint, is_reversed and is_idle properties can be used to check
    the current mission status.

    Beware that if any mobility commands are sent by your protocol or any of its plugin while a mission is in progress,
    the mission is in high risk of breaking. If sending a mobility command is necessary, stop the mission and restart
    it.
    """

    def __init__(self,
                 protocol: IProtocol,
                 configuration: MissionMobilityConfiguration = MissionMobilityConfiguration()):
        self._dispatcher = create_dispatcher(protocol)
        self._instance = protocol
        self._config = configuration
        self._logger = logging.getLogger()

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
                self._current_waypoint = len(self._current_mission) - 2
                self._is_reversed = True

        if self._current_waypoint is not None:
            if self._is_reversed:
                self._logger.info(f"Mission: Going to waypoint {self._current_waypoint} (REVERSED)")
            else:
                self._logger.info(f"Mission: Going to waypoint {self._current_waypoint}")

    def _has_overran_bounds(self) -> bool:
        if self._current_mission is None:
            return False

        if self._is_reversed:
            return self._current_waypoint < 0
        else:
            return self._current_waypoint >= len(self._current_mission)

    def _travel_to_current_waypoint(self):
        if self._current_waypoint is None:
            return

        mobility_command = GotoCoordsMobilityCommand(*self._current_mission[self._current_waypoint])
        self._instance.provider.send_mobility_command(mobility_command)

    def start_mission_with_waypoint_file(self, mission_file_path: str) -> None:
        """
        Loads a mission from a text file and afterwards calls the start mission function.
        
        The file should have the following format:

        -8.0,-4.0,0.0
        4.0,-4.0,0.0
        4.0,8.0,0.0

        The coordinates are listed in the x,y,z order and seperated by a , .

        Args:
            mission_file_path: Text file of positions the mission will follow.
        """
        mission : List[Position] = []
        
        try:
            with open(mission_file_path, 'r') as file:
                for line in file:
                    x, y, z = map(float, line.split(sep=','))
                    mission.append((x, y, z))
        except FileNotFoundError:
            print(f"Error: File '{mission_file_path}' not found.")
            exit(1)
        except ValueError:
            print(f"Error: Invalid format in file '{mission_file_path}'. Each line should contain three space-separated coordinates.")
            exit(1)

        self.start_mission(mission=mission)

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

        speed_command = SetSpeedMobilityCommand(self._config.speed)
        self._instance.provider.send_mobility_command(speed_command)

        self._logger.info("Mission: Starting mission")

    def stop_mission(self) -> None:
        """
        Stops the current mission if there is one. If there is not, does nothing.
        """
        self._current_mission = None
        self._is_reversed = False
        self._is_idle = True
        self._current_waypoint = None

        self._logger.info("Mission: Stopping mission")

    def set_current_waypoint(self, waypoint: int) -> None:
        """
        Manually sets the index of the waypoint in the mission that should be followed immediately. The mission will
        progress normally after this. If the mission is reversed, it will keep being followed in reverse direction.
        
        If there is no mission going on, will raise MissionMobilityPluginException.
        
        If waypoint is outsidef the mission bounds a MissionMobilityPluginException will be raised

        Args:
            waypoint: Index of the waypoint that should be followed next
        """
        if self._current_mission is None:
            raise MissionMobilityPluginException("Could not set waypoint: No mission in progress")
        
        if waypoint < 0 or waypoint >= len(self._current_mission):
            raise MissionMobilityPluginException(f"Could not set waypoint: Waypoint index {waypoint} is not in mission "
                                                f"bounds [0, {len(self._current_mission) - 1}]")

        self._current_waypoint = waypoint
        self._travel_to_current_waypoint()
        
    def set_reversed(self, reversed: bool) -> None:
        """
        Sets the reversed state of the mission. If True the node will start travelling the mission in reverse order
        and when False in normal order. When this method is called while the node is travelling between to a waypoint,
        the movement will be updated immediately. This means that if the node was previously traveling un-reversed, it
        will turn around and go where it came from.

        This method is only relevant when LoopMission.REVERSE is configured, in any other case this will raise
        MissionMobilityPluginException.

        Args:
            reversed: True if the node should reverse and False otherwise
        """
        if self._current_mission is None:
            raise MissionMobilityPluginException("Could not set reversed: No mission in progress")

        if self._config.loop_mission != LoopMission.REVERSE:
            raise MissionMobilityPluginException(f"Could not set reversed: Not supported loop "
                                                f"option {self._config.loop_mission.name}. "
                                                f"Only supported when loop_mission is LoopMission.REVERSE")

        old_value = self._is_reversed
        self._is_reversed = reversed

        if old_value != reversed:
            self._progress_current_waypoint()
            self._travel_to_current_waypoint()


    @property
    def current_waypoint(self) -> Optional[int]:
        """
        Current waypoint the mission is travelling to. If no mission is ongoing, returns None

        Returns:
            Current waypoint
        """
        return self._current_waypoint

    @property
    def is_reversed(self) -> bool:
        """
        If True the mission is being travelled in reverse direction because of LoopMission.REVERT. False otherwise.

        If no mission is ongoing returns False

        Returns:
            If the mission is being travelled in reverse
        """
        return self._is_reversed

    @property
    def is_idle(self) -> bool:
        """
        Returns True if the node is not following a mission. False if there is a mission in progress

        If no mission is ongoing returns True

        Returns:
            Whether there is a mission happening
        """
        return self._is_idle
