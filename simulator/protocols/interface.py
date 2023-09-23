from abc import ABC, abstractmethod

from simulator.messages.telemetry import Telemetry
from simulator.provider.interface import IProvider


class IProtocol(ABC):
    provider: IProvider

    @classmethod
    def instantiate(cls, provider: IProvider):
        protocol = cls()
        protocol.provider = provider
        return protocol

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
