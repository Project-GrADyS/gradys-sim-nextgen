import logging
from gradysim.protocol.addons.statistics import create_statistics, finish_statistics
from gradysim.protocol.messages.communication import (
    SendMessageCommand,
)
from gradysim.protocol.messages.telemetry import Telemetry
from gradysim.protocol.interface import IProtocol
from gradysim.simulator.log import SIMULATION_LOGGER
from message import ZigZagMessage, ZigZagMessageType
from utils import CommunicationStatus


class ZigZagProtocolSensor(IProtocol):
    def __init__(self):
        self.communication_status: CommunicationStatus = CommunicationStatus.FREE
        self.tentative_target: int = -1

        self._logger = logging.getLogger(SIMULATION_LOGGER)


    def initialize(self):
        self._logger.debug("Initializing sensor/ground protocol")

        create_statistics(self)

        self.provider.tracked_variables["communication_status"] = self.communication_status.name

    def handle_timer(self, timer: str):
        pass
    
    def handle_packet(self, message: str):
        message: ZigZagMessage = ZigZagMessage.from_json(message)

        if message.message_type == ZigZagMessageType.HEARTBEAT:
            self._logger.debug("Exchanging data in sensor/ground protocol")
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

            self.provider.tracked_variables["communication_status"] = self.communication_status.name

    def handle_telemetry(self, telemetry: Telemetry):
        pass

    def finish(self):
        finish_statistics(self)
