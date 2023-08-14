from protocols.IProtocol import IProtocol
from provider.IProvider import IProvider
from messages.CommunicationCommand import SendMessageCommand
from messages.Telemetry import Telemetry
from protocols.simple.SimpleMessage import SimpleMessage, SenderType


class SimpleProtocolGround(IProtocol):
    packets: int

    def initialize(self, stage: int):
        self.packets = 0

    def handle_timer(self, timer: dict):
        pass

    def handle_message(self, message: SimpleMessage):
        if message['sender'] == SenderType.DRONE:
            self.packets += message['content']
            response: SimpleMessage = {
                'sender': SenderType.GROUND_STATION,
                'content': self.packets
            }
            self.provider.send_communication_command(SendMessageCommand(response))

    def handle_telemetry(self, telemetry: Telemetry):
        pass

    def finalize(self):
        pass
