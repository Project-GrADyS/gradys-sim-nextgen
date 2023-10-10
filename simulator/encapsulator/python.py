from typing import Type

from simulator.encapsulator.interface import IEncapsulator
from simulator.messages.telemetry import Telemetry
from simulator.node.handler.mobility import MobilityHandler
from simulator.node.node import Node
from simulator.node.handler.communication import CommunicationHandler
from simulator.node.handler.timer import TimerHandler
from simulator.protocols.interface import IProtocol
from simulator.provider.python import PythonProvider


class PythonEncapsulator(IEncapsulator):
    def __init__(self,
                 node: Node,
                 communication: CommunicationHandler = None,
                 timer: TimerHandler = None,
                 mobility: MobilityHandler = None,
                 **kwargs):
        self.provider = PythonProvider(node, communication, timer, mobility)

    def encapsulate(self, protocol: Type[IProtocol]):
        self.protocol = protocol.instantiate(self.provider)

    def initialize(self, stage: int):
        self.protocol.initialize(stage)

    def handle_timer(self, timer: str):
        self.protocol.handle_timer(timer)

    def handle_packet(self, message: str):
        self.protocol.handle_packet(message)

    def handle_telemetry(self, telemetry: Telemetry):
        self.protocol.handle_telemetry(telemetry)

    def finish(self):
        pass