import logging
import random
from gradysim.protocol.plugin.statistics import create_statistics, finish_statistics
from gradysim.protocol.messages.communication import BroadcastMessageCommand
from gradysim.protocol.messages.telemetry import Telemetry
from gradysim.protocol.interface import IProtocol
from message import SimpleMessage, SenderType


class SimpleProtocolSensor(IProtocol):
    def __init__(self):
        self.packets: int = 5

        self._logger = logging.getLogger()
        
    def initialize(self):
        self._logger.debug("initializing sensor protocol")

        create_statistics(self)

        self.provider.tracked_variables["packets"] = self.packets
        self.provider.schedule_timer("", self.provider.current_time() + random.random())

    def handle_timer(self, timer: dict):
        self.packets += 1
        self.provider.tracked_variables["packets"] = self.packets
        self.provider.schedule_timer("", self.provider.current_time() + random.random())

    def handle_packet(self, message: str):
        message: SimpleMessage = SimpleMessage.from_json(message)
        self._logger.debug(f"SimpleProtocolSensor received packet: {self.packets}, {message.sender}")

        if message.sender == SenderType.DRONE:
            response = SimpleMessage(sender=SenderType.SENSOR, content=self.packets)
            self.provider.send_communication_command(
                BroadcastMessageCommand(
                    message=response.to_json())
            )

            self.packets = 0
            self.provider.tracked_variables["packets"] = self.packets

    def handle_telemetry(self, telemetry: Telemetry):
        pass

    def finish(self):
        finish_statistics(self)
