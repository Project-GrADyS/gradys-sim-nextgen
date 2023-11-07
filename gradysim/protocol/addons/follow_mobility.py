"""
This module declares two addons for the protocol: a leader and a follower. The leader broadcasts its position and the
follower follows it.

Beware that this addon controls your protocol's mobility to implement its behaviour, so you should not use any other
mobility addon with it or implement any mobility behaviour in your protocol. The MobilityLeaderAddon does not affect
the node's movement and thus should be fine to use with other mobility addons or mobility behaviour.
"""

import json
from dataclasses import dataclass
from typing import Optional, Dict, Set, Tuple

from gradysim.protocol.addons.dispatcher import create_dispatcher, DispatchReturn
from gradysim.protocol.interface import IProtocol
from gradysim.protocol.messages.communication import CommunicationCommand, CommunicationCommandType
from gradysim.protocol.messages.mobility import GotoCoordsMobilityCommand
from gradysim.protocol.messages.telemetry import Telemetry

BROADCAST_TIMER_TAG = "FollowMobilityAddon__leader_broadcast_timer"
"""
The leader will broadcast its position using a timer with this name, make sure it doesn't conflict with other timers
"""

LEADER_TAG = "FollowMobilityAddon__leader"
"""
The leader will broadcast its position using a packet with this tag, make sure it doesn't conflict with other packets
"""

FOLLOWER_TAG = "FollowMobilityAddon__follower"
"""

"""

FOLLOWER_TIMER_TAG = "FollowMobilityAddon__follower_timer"


class FollowMobilityException(Exception):
    pass


@dataclass
class MobilityLeaderConfiguration:
    broadcast_interval: float = 0.5
    """The interval at which the leader broadcasts its position"""

    follower_timeout: float = 5
    """
    If we don't receive a message from a follower for this amount of simulation seconds we consider it disconnected
    """


class MobilityLeaderAddon:
    _position: Tuple[float, float, float]

    _last_connection_from_follower: Dict[int, float]
    """Last broadcast round in which a follower was connected"""

    def __init__(self, protocol: IProtocol, configuration: MobilityLeaderConfiguration = MobilityLeaderConfiguration()):
        self._config = configuration
        self._protocol = protocol
        self._dispatcher = create_dispatcher(protocol)
        self._last_connection_from_follower = {}
        self._position = (0, 0, 0)
        self.is_broadcasting = False

        self._initialize_position_watching()
        self._initialize_broadcast()
        self._initialize_listening()

    @property
    def followers(self) -> Set[int]:
        return set(self._last_connection_from_follower.keys())

    def _cull_disconnected_followers(self) -> None:
        """Culls disconnected followers"""
        self._last_connection_from_follower = {
            follower_id: last_broadcast_round
            for follower_id, last_broadcast_round in self._last_connection_from_follower.items()
            if self._broadcast_round - last_broadcast_round < self._config.follower_timeout
        }

    def _initialize_position_watching(self) -> None:
        """Listens for position updates from the position module"""

        def position_handler(_instance: IProtocol, telemetry: Telemetry) -> DispatchReturn:
            self._position = telemetry.current_position
            return DispatchReturn.CONTINUE

        self._dispatcher.register_handle_telemetry(position_handler)

    def _initialize_broadcast(self) -> None:
        """Initializes position broadcast"""

        def broadcast_handler(_instance: IProtocol, timer: str):
            if timer != BROADCAST_TIMER_TAG:
                return DispatchReturn.CONTINUE

            leader_payload = {
                "id": self._protocol.provider.get_id(),
                "position": self._position
            }

            command = CommunicationCommand(
                CommunicationCommandType.BROADCAST,
                f"{LEADER_TAG}:{json.dumps(leader_payload)}"
            )
            self._protocol.provider.send_communication_command(command)

            self._cull_disconnected_followers()

            self._broadcast_round += 1

            self._protocol.provider.schedule_timer(
                BROADCAST_TIMER_TAG,
                self._protocol.provider.current_time() + self._config.broadcast_interval
            )
            return DispatchReturn.INTERRUPT

        self._dispatcher.register_handle_timer(broadcast_handler)

        self._protocol.provider.schedule_timer(BROADCAST_TIMER_TAG, self._config.broadcast_interval)
        self.is_broadcasting = True
        self._broadcast_round = 0

    def _initialize_listening(self) -> None:
        """Listens for messages from followers"""

        def listen_handler(_instance: IProtocol, message: str):
            if not message.startswith(FOLLOWER_TAG):
                return DispatchReturn.CONTINUE

            follower_id = int(message.split(":")[1])
            self._last_connection_from_follower[follower_id] = self._broadcast_round

            return DispatchReturn.INTERRUPT

        self._dispatcher.register_handle_packet(listen_handler)


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


class MobilityFollowerAddon:
    _leader: Optional[int] = None
    _leader_position: Optional[Tuple[float, float, float]] = None

    _relative_position: Tuple[float, float, float] = (0, 0, 0)

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

                # Going to the leader's position at relative coordinates
                destination = (coord + relative_coord
                               for coord, relative_coord in zip(self._leader_position, self._relative_position))
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
    def relative_position(self) -> Tuple[float, float, float]:
        return self._relative_position

    @property
    def current_leader_position(self) -> Optional[Tuple[float, float, float]]:
        return self._leader_position

    def follow_leader(self, leader_id: int) -> None:
        if leader_id not in self.available_leaders:
            raise FollowMobilityException(f"Leader {leader_id} is not available")
        self._leader = leader_id

    def set_relative_position(self, position: Tuple[float, float, float]) -> None:
        self._relative_position = position
