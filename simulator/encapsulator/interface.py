from abc import ABC, abstractmethod
from typing import Type, Generic, TypeVar

from simulator.messages.telemetry import Telemetry
from protocol.interface import IProtocol

T = TypeVar("T", bound=IProtocol)


class IEncapsulator(ABC, Generic[T]):
    protocol: T

    @abstractmethod
    def encapsulate(self, protocol: Type[T]):
        pass

    @abstractmethod
    def initialize(self, stage: int):
        pass

    @abstractmethod
    def handle_timer(self, timer: str):
        pass

    @abstractmethod
    def handle_packet(self, message: str):
        pass

    @abstractmethod
    def handle_telemetry(self, telemetry: Telemetry):
        pass

    @abstractmethod
    def finish(self):
        pass
