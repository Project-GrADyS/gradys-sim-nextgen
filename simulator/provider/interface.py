from abc import ABC, abstractmethod
from typing import Any, Dict

from simulator.messages.communication import CommunicationCommand
from simulator.messages.mobility import MobilityCommand


class IProvider(ABC):
    @abstractmethod
    def send_communication_command(self, command: CommunicationCommand):
        pass

    @abstractmethod
    def send_mobility_command(self, command: MobilityCommand):
        pass

    @abstractmethod
    def schedule_timer(self, timer: str, timestamp: float):
        pass

    @abstractmethod
    def current_time(self) -> float:
        pass

    tracked_variables: Dict[str, Any]
