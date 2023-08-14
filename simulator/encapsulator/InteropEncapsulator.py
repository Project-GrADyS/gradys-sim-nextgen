from enum import Enum
from typing import Tuple, Union, List, Type

from encapsulator.IEncapsulator import IEncapsulator
from messages.CommunicationCommand import CommunicationCommand
from messages.MobilityCommand import MobilityCommand
from protocols.IProtocol import IProtocol
from provider.IProvider import IProvider


class _ConsequenceType(Enum):
    COMMUNICATION = 1
    MOBILITY = 2
    TIMER = 3


_TimerParams = Tuple[dict, float]

_Consequence = Tuple[_ConsequenceType, Union[CommunicationCommand, MobilityCommand, _TimerParams]]


class _InteropProvider(IProvider):
    consequences: List[_Consequence]
    timestamp: int

    def __init__(self):
        self.consequences = []
        self.timestamp = 0

    def send_communication_command(self, command: CommunicationCommand):
        self.consequences.append((_ConsequenceType.COMMUNICATION, command))

    def send_mobility_command(self, command: MobilityCommand):
        self.consequences.append((_ConsequenceType.MOBILITY, command))

    def schedule_timer(self, timer: dict, timestamp: float):
        self.consequences.append((_ConsequenceType.TIMER, (timer, timestamp)))

    def current_time(self) -> int:
        return self.timestamp


class InteropEncapsulator(IEncapsulator):
    provider: _InteropProvider

    @classmethod
    def encapsulate(cls, protocol: Type[IProtocol]):
        encapsulator = cls()

        encapsulator.provider = _InteropProvider()
        encapsulator.protocol = protocol.instantiate(encapsulator.provider)
        return encapsulator

    def _collect_consequences(self) -> List[_Consequence]:
        consequences = self.provider.consequences
        self.provider.consequences = []
        return consequences

    def set_timestamp(self, timestamp: int):
        self.provider.timestamp = timestamp

    def initialize(self, stage: int) -> List[_Consequence]:
        self.protocol.initialize(stage)
        return self._collect_consequences()

    def handle_timer(self, timer: dict) -> List[_Consequence]:
        self.protocol.handle_timer(timer)
        return self._collect_consequences()

    def handle_message(self, message: dict) -> List[_Consequence]:
        self.protocol.handle_message(message)
        return self._collect_consequences()

    def finalize(self) -> List[_Consequence]:
        self.protocol.finalize()
        return self._collect_consequences()
