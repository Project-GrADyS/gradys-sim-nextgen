import json
from dataclasses import dataclass
from typing import Optional, Dict, Set

from gradysim.protocol.interface import IProtocol
from gradysim.protocol.messages.communication import CommunicationCommand, CommunicationCommandType
from gradysim.protocol.messages.mobility import GotoCoordsMobilityCommand
from gradysim.protocol.plugin.dispatcher import create_dispatcher, DispatchReturn
from gradysim.protocol.plugin.follow_mobility.mobility import LEADER_TAG, FOLLOWER_TAG, FOLLOWER_TIMER_TAG
from gradysim.protocol.position import Position, rotate_position_2d

class FollowMobilityException(Exception):
    pass

@dataclass
class MobilityFollowerConfiguration:
    scanning_interval: float = 0.5
    """
    Interval between leader scans, in simulation seconds. The follower will update the list of leaders and the current 
    leader.
    """

    leader_timeout: float = 2
    """
    After this amount of simulation seconds without receiving a broadcast from the leader, we consider it
    disconnected
    """

    auto_follow: bool = True
    """
    Automatically follows the first leader available if set to True. If set to False, the user must call 
    follow_leader manually. If True the user can still call follow_leader to follow a specific leader, but if connection
    to that leader is lost the follower will automatically follow the first leader available.
    """

    follow_orientation: bool = True
    """
    Whether the follower's relative position should shift with the leader's orientation.
    If True, relative (X, Y) is rotated by the leader's orientation.
    If False, relative position remains fixed in world coordinates.
    """


class MobilityFollowerPlugin:
    _leader: Optional[int] = None
    _leader_position: Optional[Position] = None
    _leader_orientation: Optional[float] = None

    _relative_position: Position = (0, 0, 0)

    _last_leader_broadcast: Dict[int, float]

    def __init__(self, protocol: IProtocol,
                 configuration: MobilityFollowerConfiguration = MobilityFollowerConfiguration()):
        self._config = configuration

        self._protocol = protocol
        self._dispatcher = create_dispatcher(protocol)

        self._last_leader_broadcast = {}

        self._initialize_following()
        self._initialize_scanning()

    def _initialize_following(self):
        """Initializes leader following behaviour"""

        def follow_handler(_instance: IProtocol, message: str):
            if not message.startswith(LEADER_TAG):
                return DispatchReturn.CONTINUE

            leader_payload = json.loads(message[len(f"{LEADER_TAG}:"):])
            leader_id = leader_payload["id"]
            self._last_leader_broadcast[leader_id] = self._protocol.provider.current_time()

            if leader_id == self._leader:
                self._leader_position = leader_payload["position"]
                self._leader_orientation = leader_payload.get("orientation", 0.0)

                if self._config.follow_orientation and self._leader_orientation is not None:
                    relative_position = rotate_position_2d(self._relative_position, self._leader_orientation)
                else:
                    relative_position = self._relative_position

                # Going to the leader's position at relative coordinates
                destination = (coord + relative_coord
                               for coord, relative_coord in zip(self._leader_position, relative_position))
                mobility_command = GotoCoordsMobilityCommand(*destination)
                self._protocol.provider.send_mobility_command(mobility_command)

                # Informing the leader that we are following him
                command = CommunicationCommand(
                    CommunicationCommandType.SEND,
                    f"{FOLLOWER_TAG}:{self._protocol.provider.get_id()}",
                    leader_id
                )
                self._protocol.provider.send_communication_command(command)

            return DispatchReturn.INTERRUPT

        self._dispatcher.register_handle_packet(follow_handler)

    def _initialize_scanning(self):
        """Periodically updates the list of current leaders"""

        def scan_handler(_instance: IProtocol, timer: str):
            if timer != FOLLOWER_TIMER_TAG:
                return DispatchReturn.CONTINUE

            self._last_leader_broadcast = {
                leader_id: last_broadcast
                for leader_id, last_broadcast in self._last_leader_broadcast.items()
                if self._protocol.provider.current_time() - last_broadcast < self._config.leader_timeout
            }

            if self._leader is not None and self._leader not in self._last_leader_broadcast:
                self._leader = None
                self._leader_position = None
                self._leader_orientation = None

            if self._leader is None and len(self.available_leaders) > 0:
                self.follow_leader(list(self.available_leaders)[0])

            self._protocol.provider.schedule_timer(
                FOLLOWER_TIMER_TAG,
                self._protocol.provider.current_time() + self._config.scanning_interval
            )
            return DispatchReturn.INTERRUPT

        self._dispatcher.register_handle_timer(scan_handler)

        self._protocol.provider.schedule_timer(FOLLOWER_TIMER_TAG, self._config.scanning_interval)

    @property
    def available_leaders(self) -> Set[int]:
        return set(self._last_leader_broadcast.keys())

    @property
    def current_leader(self) -> Optional[int]:
        return self._leader

    @property
    def relative_position(self) -> Position:
        return self._relative_position

    @property
    def current_leader_position(self) -> Optional[Position]:
        return self._leader_position

    @property
    def current_leader_orientation(self) -> Optional[float]:
        return self._leader_orientation

    def follow_leader(self, leader_id: int) -> None:
        if leader_id not in self.available_leaders:
            raise FollowMobilityException(f"Leader {leader_id} is not available")
        self._leader = leader_id

    def set_relative_position(self, position: Position) -> None:
        self._relative_position = position