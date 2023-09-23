from abc import ABC, abstractmethod
from typing import Type

from simulator.messages.telemetry import Telemetry
from simulator.protocols.interface import IProtocol


class IEncapsulator(ABC):
    protocol: IProtocol

    @abstractmethod
    def encapsulate(self, protocol: Type[IProtocol]):
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
