from typing import Type

from simulator.encapsulator.interface import IEncapsulator
from simulator.messages.communication import CommunicationCommand
from simulator.messages.mobility import MobilityCommand
from simulator.messages.telemetry import Telemetry
from simulator.node import Node
from simulator.node.handler.communication import CommunicationHandler
from simulator.protocols.interface import IProtocol
from simulator.provider.interface import IProvider


class _PythonProvider(IProvider):
    def __init__(self, node: Node, communication_handler: CommunicationHandler):
        self.node = node
        self.communication_handler = communication_handler

    def send_communication_command(self, command: CommunicationCommand):
        self.communication_handler.handle_command(command, self.node)

    def send_mobility_command(self, command: MobilityCommand):
        pass

    def schedule_timer(self, timer: dict, timestamp: float):
        pass

    def current_time(self) -> float:
        pass


class PythonEncapsulator(IEncapsulator):
    def __init__(self, node: Node, communication: CommunicationHandler):
        self.provider = _PythonProvider(node, communication)

    def encapsulate(self, protocol: Type[IProtocol]):
        self.protocol = protocol.instantiate(self.provider)

    def initialize(self, stage: int):
        self.protocol.initialize(stage)

    def handle_timer(self, timer: dict):
        self.protocol.handle_timer(timer)

    def handle_packet(self, message: dict):
        self.protocol.handle_packet(message)

    def handle_telemetry(self, telemetry: Telemetry):
        self.protocol.handle_telemetry(telemetry)

    def finish(self):
        pass