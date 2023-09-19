from typing import List, Type

from simulator.encapsulator.interface import IEncapsulator

from simulator.messages.telemetry import Telemetry
from simulator.protocols.interface import IProtocol
from simulator.provider.interop import InteropProvider, Consequence


class InteropEncapsulator(IEncapsulator):
    provider: InteropProvider

    def __init__(self):
        self.provider = InteropProvider()

    def encapsulate(self, protocol: Type[IProtocol]):
        self.protocol = protocol.instantiate(self.provider)

    def _collect_consequences(self) -> List[Consequence]:
        consequences = self.provider.consequences
        self.provider.consequences = []
        return consequences

    def set_timestamp(self, timestamp: float):
        self.provider.timestamp = timestamp

    def initialize(self, stage: int) -> List[Consequence]:
        self.protocol.initialize(stage)
        return self._collect_consequences()

    def handle_timer(self, timer: str) -> List[Consequence]:
        self.protocol.handle_timer(timer)
        return self._collect_consequences()

    def handle_packet(self, message: str) -> List[Consequence]:
        self.protocol.handle_packet(message)
        return self._collect_consequences()

    def handle_telemetry(self, telemetry: Telemetry) -> List[Consequence]:
        self.protocol.handle_telemetry(telemetry)
        return self._collect_consequences()

    def finish(self) -> List[Consequence]:
        self.protocol.finish()
        return self._collect_consequences()
