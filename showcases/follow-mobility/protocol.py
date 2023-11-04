import random

from gradys.protocol.addons.follow_mobility import MobilityFollowerAddon, MobilityLeaderAddon
from gradys.protocol.addons.random_mobility import RandomMobilityAddon
from gradys.protocol.interface import IProtocol
from gradys.protocol.messages.mobility import SetSpeedMobilityCommand
from gradys.protocol.messages.telemetry import Telemetry


class FollowerProtocol(IProtocol):
    follower: MobilityFollowerAddon

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

        self.provider.schedule_timer("", self.provider.current_time() + 0.1)

    def handle_packet(self, message: str) -> None:
        pass

    def handle_telemetry(self, telemetry: Telemetry) -> None:
        pass

    def finish(self) -> None:
        pass


class LeaderProtocol(IProtocol):
    def initialize(self, stage: int) -> None:
        MobilityLeaderAddon(self)
        random = RandomMobilityAddon(self)
        random.initiate_random_trip()

        command = SetSpeedMobilityCommand(5)
        self.provider.send_mobility_command(command)

    def handle_timer(self, timer: str) -> None:
        pass

    def handle_packet(self, message: str) -> None:
        pass

    def handle_telemetry(self, telemetry: Telemetry) -> None:
        pass

    def finish(self) -> None:
        pass
