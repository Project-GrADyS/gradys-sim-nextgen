import logging
import random

from gradysim.protocol.interface import IProtocol
from gradysim.simulator.log import SIMULATION_LOGGER
from gradysim.protocol.messages.communication import CommunicationCommand, CommunicationCommandType
from gradysim.protocol.messages.telemetry import Telemetry
from gradysim.protocol.addons.random_mobility import RandomMobilityAddon


class PingProtocol(IProtocol):
    sent: int = 0
    received: int = 0

    def __init__(self):
        self._logger = logging.getLogger(SIMULATION_LOGGER)
        self._movement = RandomMobilityAddon(self)

    def initialize(self, stage: int):
        self.provider.schedule_timer("", self.provider.current_time() + random.random() + 2)
        self._movement.initiate_random_trip()

    def handle_timer(self, timer: dict):
        command = CommunicationCommand(
            CommunicationCommandType.BROADCAST,
            "ping"
        )
        self._logger.info("ping")
        self.provider.send_communication_command(command)
        self.sent += 1
        self.provider.schedule_timer("", self.provider.current_time() + 2)

    def handle_packet(self, message: str):
        if message == "ping":
            self.received += 1
            self._logger.info("pong")

    def handle_telemetry(self, telemetry: Telemetry):
        pass

    def finish(self):
        self._movement.initiate_random_trip()
