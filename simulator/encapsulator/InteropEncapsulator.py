from typing import List, Type

from simulator.encapsulator.IEncapsulator import IEncapsulator
from simulator.messages.CommunicationCommand import CommunicationCommand
from simulator.messages.MobilityCommand import MobilityCommand
from simulator.messages.Telemetry import Telemetry
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

    def set_timestamp(self, timestamp: float):
        self.provider.timestamp = timestamp

    def initialize(self, stage: int) -> List[Consequence]:
        self.protocol.initialize(stage)
        return self._collect_consequences()

    def handle_timer(self, timer: dict) -> List[Consequence]:
        self.protocol.handle_timer(timer)
        return self._collect_consequences()

    def handle_packet(self, message: dict) -> List[Consequence]:
        self.protocol.handle_packet(message)
        return self._collect_consequences()

    def handle_telemetry(self, telemetry: Telemetry) -> List[Consequence]:
        self.protocol.handle_telemetry(telemetry)
        return self._collect_consequences()

    def finish(self) -> List[Consequence]:
        self.protocol.finish()
        return self._collect_consequences()
