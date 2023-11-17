from gradysim.protocol.messages.communication import (
    SendMessageCommand,
)
from gradysim.protocol.messages.telemetry import Telemetry
from gradysim.protocol.interface import IProtocol
from message import ZigZagMessage, ZigZagMessageType
from utils import CommunicationStatus


class ZigZagProtocolSensor(IProtocol):
    timeout_duration: int = 0
    communication_status: CommunicationStatus = CommunicationStatus.FREE
    tentative_target: int = -1
    last_target: int = -1
    tentative_target_name: str = ""
    data_load_signal_id: str = ""

    def initialize(self):
        pass

    def handle_timer(self, timer: str):
        self.packets += 1
        self.provider.tracked_variables["packets"] = self.packets
        self.provider.schedule_timer("", self.provider.current_time() + 2)

    def handle_packet(self, message: str):
        message: ZigZagMessage = ZigZagMessage.from_json(message)
        print(f"ZigZag Sensor protocol received packet")

        if message.message_type == ZigZagMessageType.HEARTBEAT:
            self.tentative_target = message.source_id

            message = ZigZagMessage(
                message_type=ZigZagMessageType.BEARER,
                source_id=self.provider.get_id(),
                destination_id=self.tentative_target,
            )
            self.provider.send_communication_command(
                SendMessageCommand(
                    message=message.to_json(),
                    destination=self.tentative_target,
                )
            )

    def handle_telemetry(self, telemetry: Telemetry):
        pass

    def finish(self):
        pass
