from enum import Enum
from typing import List, Type, Tuple, Union, Any, Callable

from protocol.interface import IProtocol
from encapsulator.interface import IEncapsulator
from protocol.messages.communication import CommunicationCommand
from protocol.messages.mobility import MobilityCommand

from protocol.messages.telemetry import Telemetry
from protocol.provider import IProvider


class ConsequenceType(int, Enum):
    COMMUNICATION = 0
    MOBILITY = 1
    TIMER = 2
    TRACK_VARIABLE = 3


TimerParams = Tuple[dict, float]

TrackVariableParams = Tuple[str, Any]

Consequence = Tuple[ConsequenceType, Union[CommunicationCommand, MobilityCommand, TimerParams, TrackVariableParams]]


class _TrackedVariableContainer(dict):
    def __init__(self, setter_callback: Callable[[str, Any], None]):
        super().__init__()
        self.callback = setter_callback

    def __setitem__(self, key, value):
        self.callback(key, value)


class InteropProvider(IProvider):
    consequences: List[Consequence]
    timestamp: int

    def __init__(self):
        self.consequences = []
        self.timestamp = 0
        self.tracked_variables = \
            _TrackedVariableContainer(lambda key, value: self.consequences.append((ConsequenceType.TRACK_VARIABLE,
                                                                                   (key, value))))

    def send_communication_command(self, command: CommunicationCommand):
        self.consequences.append((ConsequenceType.COMMUNICATION, command))

    def send_mobility_command(self, command: MobilityCommand):
        self.consequences.append((ConsequenceType.MOBILITY, command))

    def schedule_timer(self, timer: str, timestamp: float):
        self.consequences.append((ConsequenceType.TIMER, (timer, timestamp)))

    def current_time(self) -> int:
        return self.timestamp


class InteropEncapsulator(IEncapsulator):
    provider: InteropProvider

    def __init__(self):
        self.provider = InteropProvider()

    def encapsulate(self, protocol: Type[IProtocol]):
        self.protocol = protocol.instantiate(self.provider)

    def _collect_consequences(self) -> List[Consequence]:
        consequences = self.provider.consequences
        self.provider.consequences = []
        return consequences

    def set_timestamp(self, timestamp: float):
        self.provider.timestamp = timestamp

    def initialize(self, stage: int) -> List[Consequence]:
        self.protocol.initialize(stage)
        return self._collect_consequences()

    def handle_timer(self, timer: str) -> List[Consequence]:
        self.protocol.handle_timer(timer)
        return self._collect_consequences()

    def handle_packet(self, message: str) -> List[Consequence]:
        self.protocol.handle_packet(message)
        return self._collect_consequences()

    def handle_telemetry(self, telemetry: Telemetry) -> List[Consequence]:
        self.protocol.handle_telemetry(telemetry)
        return self._collect_consequences()

    def finish(self) -> List[Consequence]:
        self.protocol.finish()
        return self._collect_consequences()
