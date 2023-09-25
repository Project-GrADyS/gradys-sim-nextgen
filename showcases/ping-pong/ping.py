import random

from simulator.messages.communication import CommunicationCommand, CommunicationCommandType
from simulator.messages.telemetry import Telemetry
from simulator.protocols.interface import IProtocol


class PingProtocol(IProtocol):
    def initialize(self, stage: int):
        self.provider.schedule_timer("", self.provider.current_time() + random.random() + 2)

    def handle_timer(self, timer: dict):
        command = CommunicationCommand(
            CommunicationCommandType.BROADCAST,
            "ping"
        )
        self.provider.send_communication_command(command)
        self.provider.schedule_timer("", self.provider.current_time() + 2)

    def handle_packet(self, message: str):
        if message == "ping":
            command = CommunicationCommand(
                CommunicationCommandType.BROADCAST,
                "pong"
            )
            self.provider.send_communication_command(command)

    def handle_telemetry(self, telemetry: Telemetry):
        pass

    def finish(self):
        pass
