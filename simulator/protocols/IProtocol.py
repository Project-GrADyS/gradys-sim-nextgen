from abc import ABC, abstractmethod

from provider.IProvider import IProvider


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
    def handle_timer(self, timer: dict):
        pass

    @abstractmethod
    def handle_message(self, message: dict):
        pass

    @abstractmethod
    def finalize(self):
        pass
