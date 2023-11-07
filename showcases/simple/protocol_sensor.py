import random
from gradysim.protocol.messages.communication import SendMessageCommand
from gradysim.protocol.messages.telemetry import Telemetry
from gradysim.protocol.interface import IProtocol
from message import SimpleMessage, SenderType


class SimpleProtocolSensor(IProtocol):
    packets: int

    def initialize(self, stage: int):
        self.packets = 5
        self.provider.tracked_variables["packets"] = self.packets
        self.provider.schedule_timer({}, self.provider.current_time() + random.random())

    def handle_timer(self, timer: dict):
        self.packets += 1
        self.provider.tracked_variables["packets"] = self.packets
        self.provider.schedule_timer({}, self.provider.current_time() + 2)

    def handle_packet(self, message: str):
        message: SimpleMessage = SimpleMessage.from_json(message)
        print(f"SimpleProtocolSensor received packet: {self.packets}, {message.sender}")

        if message.sender == SenderType.DRONE:
            response = SimpleMessage(sender=SenderType.SENSOR, content=self.packets)
            self.provider.send_communication_command(
                SendMessageCommand(response.to_json())
            )

            self.packets = 0
            self.provider.tracked_variables["packets"] = self.packets

    def handle_telemetry(self, telemetry: Telemetry):
        pass

    def finish(self):
        pass
