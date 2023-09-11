from enum import Enum
from typing import Tuple, Any, Union, Callable, List

from simulator.messages.CommunicationCommand import CommunicationCommand
from simulator.messages.MobilityCommand import MobilityCommand
from simulator.provider.IProvider import IProvider


class ConsequenceType(Enum):
    COMMUNICATION = 1
    MOBILITY = 2
    TIMER = 3
    TRACK_VARIABLE = 4


TimerParams = Tuple[dict, float]

TrackVariableParams = Tuple[str, Any]

Consequence = Tuple[ConsequenceType, Union[CommunicationCommand, MobilityCommand, TimerParams, TrackVariableParams]]


class _TrackedVariableContainer(dict):
    def __init__(self, setter_callback: Callable[[str, Any], None]):
        super().__init__()
        self.callback = setter_callback

    def __setitem__(self, key, value):
        self.callback(key, value)
        self[key] = value


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

    def schedule_timer(self, timer: dict, timestamp: float):
        self.consequences.append((ConsequenceType.TIMER, (timer, timestamp)))

    def current_time(self) -> int:
        return self.timestamp