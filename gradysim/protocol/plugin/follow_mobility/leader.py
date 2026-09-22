import json
from dataclasses import dataclass
from typing import Dict, Set

from gradysim.protocol.interface import IProtocol
from gradysim.protocol.messages.communication import CommunicationCommand, CommunicationCommandType
from gradysim.protocol.messages.telemetry import Telemetry
from gradysim.protocol.plugin.dispatcher import create_dispatcher, DispatchReturn
from gradysim.protocol.plugin.follow_mobility.mobility import LEADER_TAG, BROADCAST_TIMER_TAG, FOLLOWER_TAG
from gradysim.protocol.position import Position



@dataclass
class MobilityLeaderConfiguration:
    broadcast_interval: float = 0.02
    """The interval at which the leader broadcasts its position"""

    follower_timeout: float = 5
    """
    If we don't receive a message from a follower for this amount of simulation seconds we consider it disconnected
    """

    initial_orientation: float = 0.0
    """The initial orientation of the leader in degrees (0° along +X, 90° along +Y)"""

class MobilityLeaderPlugin:
    _position: Position
    _orientation: float

    _last_connection_from_follower: Dict[int, float]
    """Last broadcast round in which a follower was connected"""

    def __init__(self, protocol: IProtocol, configuration: MobilityLeaderConfiguration = MobilityLeaderConfiguration()):
        self._config = configuration
        self._protocol = protocol
        self._dispatcher = create_dispatcher(protocol)
        self._last_connection_from_follower = {}
        self._position = (0, 0, 0)
        self._orientation = configuration.initial_orientation
        self.is_broadcasting = False

        self._initialize_position_watching()
        self._initialize_broadcast()
        self._initialize_listening()

    @property
    def orientation(self) -> float:
        return self._orientation

    def set_orientation(self, orientation: float) -> None:
        self._orientation = orientation

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
                "position": self._position,
                "orientation": self._orientation
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
