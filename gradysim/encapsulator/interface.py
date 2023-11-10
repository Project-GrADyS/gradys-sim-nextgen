from abc import ABC, abstractmethod
from typing import Type, Generic, TypeVar

from gradysim.protocol.messages.telemetry import Telemetry
from gradysim.protocol.interface import IProtocol

T = TypeVar("T", bound=IProtocol)


class IEncapsulator(ABC, Generic[T]):
    """
    Defines a generic interface that all encapsulators should implement. Encapsulator's main task is to wrap nodes
    absorbing effects from the environment and propagating them to the node and injecting a provider instance so
    that the nodes can interact with the environment.
    """
    protocol: T

    @abstractmethod
    def encapsulate(self, protocol: Type[T]) -> None:
        """
        Wraps a protocol. Should instantiate it and inject a provider instance into it. Every IEncapsulator instance
        wraps a single protocol only.

        Args:
            protocol: The type of protocol being instantiated
        """
        pass

    @abstractmethod
    def initialize(self, stage: int):
        """
        Wraps the protocols initialize function
        """
        pass

    @abstractmethod
    def handle_timer(self, timer: str):
        """
        Wraps the protocols handler_timer function
        """
        pass

    @abstractmethod
    def handle_packet(self, message: str):
        """
        Wraps the protocols handle_packet function
        """
        pass

    @abstractmethod
    def handle_telemetry(self, telemetry: Telemetry):
        """
        Wraps the protocols handle_telemetry function
        """
        pass

    @abstractmethod
    def finish(self):
        """
        Wraps the protocols finish function
        """
        pass
