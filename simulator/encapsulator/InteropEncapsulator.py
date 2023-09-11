from typing import List, Type

from simulator.encapsulator.IEncapsulator import IEncapsulator
from simulator.protocols.IProtocol import IProtocol
from simulator.provider.InteropProvider import InteropProvider, Consequence


class InteropEncapsulator(IEncapsulator):
    provider: InteropProvider

    @classmethod
    def encapsulate(cls, protocol: Type[IProtocol]):
        encapsulator = cls()

        encapsulator.provider = InteropProvider()
        encapsulator.protocol = protocol.instantiate(encapsulator.provider)
        return encapsulator

    def _collect_consequences(self) -> List[Consequence]:
        consequences = self.provider.consequences
        self.provider.consequences = []
        return consequences

    def set_timestamp(self, timestamp: int):
        self.provider.timestamp = timestamp

    def initialize(self, stage: int) -> List[Consequence]:
        self.protocol.initialize(stage)
        return self._collect_consequences()

    def handle_timer(self, timer: dict) -> List[Consequence]:
        self.protocol.handle_timer(timer)
        return self._collect_consequences()

    def handle_message(self, message: dict) -> List[Consequence]:
        self.protocol.handle_message(message)
        return self._collect_consequences()

    def finalize(self) -> List[Consequence]:
        self.protocol.finalize()
        return self._collect_consequences()
