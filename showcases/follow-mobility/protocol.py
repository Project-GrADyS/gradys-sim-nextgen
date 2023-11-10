import logging
import random

from gradysim.protocol.addons.follow_mobility import MobilityFollowerAddon, MobilityLeaderAddon
from gradysim.protocol.addons.random_mobility import RandomMobilityAddon
from gradysim.protocol.interface import IProtocol
from gradysim.protocol.messages.mobility import SetSpeedMobilityCommand
from gradysim.protocol.messages.telemetry import Telemetry
from gradysim.simulator.log import SIMULATION_LOGGER


class FollowerProtocol(IProtocol):
    follower: MobilityFollowerAddon

    def __init__(self):
        self._logger = logging.getLogger(SIMULATION_LOGGER)

    def initialize(self, stage: int) -> None:
        self.follower = MobilityFollowerAddon(self)

        self.follower.set_relative_position((
            random.uniform(-5, 5),
            random.uniform(-5, 5),
            random.uniform(0, 5)
        ))

        self.provider.schedule_timer("", 0.1)

    def handle_timer(self, timer: str) -> None:
        if self.follower.current_leader is None and len(self.follower.available_leaders) > 0:
            self.follower.follow_leader(list(self.follower.available_leaders)[0])

        self._logger.info(f"Following leader: {self.follower.current_leader}")

        self.provider.schedule_timer("", self.provider.current_time() + 1)

    def handle_packet(self, message: str) -> None:
        pass

    def handle_telemetry(self, telemetry: Telemetry) -> None:
        pass

    def finish(self) -> None:
        pass


class LeaderProtocol(IProtocol):
    leader: MobilityLeaderAddon

    def __init__(self):
        self._logger = logging.getLogger(SIMULATION_LOGGER)

    def initialize(self, stage: int) -> None:
        self.leader = MobilityLeaderAddon(self)
        random = RandomMobilityAddon(self)
        random.initiate_random_trip()

        command = SetSpeedMobilityCommand(5)
        self.provider.send_mobility_command(command)
        self.provider.schedule_timer("", self.provider.current_time() + 1)

    def handle_timer(self, timer: str) -> None:
        self._logger.info(f"Being followed by: {self.leader.followers}")

        self.provider.schedule_timer("", self.provider.current_time() + 1)

    def handle_packet(self, message: str) -> None:
        pass

    def handle_telemetry(self, telemetry: Telemetry) -> None:
        pass

    def finish(self) -> None:
        pass
