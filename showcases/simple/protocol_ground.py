from gradysim.protocol.messages.communication import SendMessageCommand
from gradysim.protocol.messages.telemetry import Telemetry
from gradysim.protocol.interface import IProtocol
from message import SimpleMessage, SenderType


class SimpleProtocolGround(IProtocol):
    packets: int

    def initialize(self, stage: int):
        self.packets = 0
        self.provider.tracked_variables["packets"] = self.packets

    def handle_timer(self, timer: dict):
        pass

    def handle_packet(self, message: str):
        message: SimpleMessage = SimpleMessage.from_json(message)
        print(f"SimpleProtocolGround received packet: {self.packets}, {message.sender}")

        if message.sender == SenderType.DRONE:
            self.packets += message.content
            self.provider.tracked_variables["packets"] = self.packets

            response = SimpleMessage(
                sender=SenderType.GROUND_STATION, content=self.packets
            )
            self.provider.send_communication_command(
                SendMessageCommand(response.to_json())
            )

    def handle_telemetry(self, telemetry: Telemetry):
        pass

    def finish(self):
        pass
