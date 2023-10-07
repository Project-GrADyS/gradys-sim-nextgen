import logging
import random

from simulator.log import SIMULATION_LOGGER
from simulator.messages.communication import CommunicationCommand, CommunicationCommandType
from simulator.messages.telemetry import Telemetry
from simulator.protocols.addons.random_mobility import RandomMobilityAddon
from simulator.protocols.interface import IProtocol


class PingProtocol(IProtocol):
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
        self.provider.schedule_timer("", self.provider.current_time() + 2)

    def handle_packet(self, message: str):
        if message == "ping":
            self._logger.info("pong")

    def handle_telemetry(self, telemetry: Telemetry):
        pass

    def finish(self):
        self._movement.initiate_random_trip()
