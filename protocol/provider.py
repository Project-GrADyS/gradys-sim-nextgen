from abc import ABC, abstractmethod
from typing import Any, Dict

from protocol.messages.communication import CommunicationCommand
from protocol.messages.mobility import MobilityCommand


class IProvider(ABC):
    @abstractmethod
    def send_communication_command(self, command: CommunicationCommand) -> None:
        """
        Sends a communication command to the node's communication module
        """
        pass

    @abstractmethod
    def send_mobility_command(self, command: MobilityCommand) -> None:
        """
        Sends a mobility command to the node's mobility module
        """
        pass

    @abstractmethod
    def schedule_timer(self, timer: str, timestamp: float) -> None:
        """
        Schedules a timer that should fire at a specified timestamp
        """
        pass

    @abstractmethod
    def current_time(self) -> float:
        """
        Returns the current simulator time
        """
        pass

    tracked_variables: Dict[str, Any]
