from abc import ABC, abstractmethod

from simulator.messages.telemetry import Telemetry
from simulator.provider.interface import IProvider


class IProtocol(ABC):
    provider: IProvider
    """
    IProvider instance that will provide protocol
    with necessary tools to function
    """

    @classmethod
    def instantiate(cls, provider: IProvider) -> 'IProtocol':
        """
        Called when the protocol is instantiated before the simulation starts.
        This function is important because it is where the IProvider instance
        is injected into the protocol.
        """
        protocol = cls()
        protocol.provider = provider
        return protocol

    @abstractmethod
    def initialize(self, stage: int) -> None:
        """
        This is the first function called when the simulation begins. The initialize()
        methods for each network node are called in arbitrary order so don't rely on other
        protocols having already been initialized.
        """
        pass

    @abstractmethod
    def handle_timer(self, timer: str) -> None:
        """
        Called when a previously scheduled timer fires
        :param timer: the timer that fired
        """
        pass

    @abstractmethod
    def handle_packet(self, message: str) -> None:
        """
        Called when a packet is received from another node.
        """
        pass

    @abstractmethod
    def handle_telemetry(self, telemetry: Telemetry) -> None:
        """
        Regularly called by the mobility module with information
        about the state of the node's mobility.
        """
        pass

    @abstractmethod
    def finish(self) -> None:
        """
        Called when the simulation finishes. The finish() method
        of every node in the simulation is called in arbitrary
        order.
        """
        pass
