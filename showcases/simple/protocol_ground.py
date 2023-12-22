import logging
from gradysim.protocol.plugin.statistics import create_statistics, finish_statistics
from gradysim.protocol.messages.communication import BroadcastMessageCommand
from gradysim.protocol.messages.telemetry import Telemetry
from gradysim.protocol.interface import IProtocol
from message import SimpleMessage, SenderType


class SimpleProtocolGround(IProtocol):
    def __init__(self):
        self.packets: int = 0

        self._logger = logging.getLogger()

    def initialize(self):
        self._logger.debug("Initializing mobile protocol")

        create_statistics(self)

        self.provider.tracked_variables["packets"] = self.packets

    def handle_timer(self, timer: str):
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
                BroadcastMessageCommand(response.to_json())
            )

    def handle_telemetry(self, telemetry: Telemetry):
        pass

    def finish(self):
        finish_statistics(self)
        