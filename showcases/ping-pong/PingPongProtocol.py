import random
from simulator.messages.CommunicationCommand import CommunicationCommandType, CommunicationCommand
from simulator.messages.Telemetry import Telemetry
from simulator.protocols.IProtocol import IProtocol


class PingPongProtocol(IProtocol):
    def initialize(self, stage: int):
        # The addition of the random delay prevents a situation where messages are sent at the same
        # time and collide. This is not an issue on experiment mode but on integrated and the real
        # world it is a very real issue.
        self.provider.schedule_timer({}, self.provider.current_time() + 2 + random.random())

    def handle_timer(self, timer: dict):
        command: CommunicationCommand = CommunicationCommand(CommunicationCommandType.BROADCAST, {
            "type": "Ping"
        })
        self.provider.send_communication_command(command)
        self.provider.schedule_timer({}, self.provider.current_time())

    def handle_packet(self, message: dict):
        if message['type'] == "Ping":
            command: CommunicationCommand = CommunicationCommand(CommunicationCommandType.BROADCAST, {
                "type": "pong"
            })
        else:
            command: CommunicationCommand = CommunicationCommand(CommunicationCommandType.BROADCAST, {
                "type": "pong"
            })
        self.provider.send_communication_command(command)

    def handle_telemetry(self, telemetry: Telemetry):
        pass

    def finish(self):
        pass