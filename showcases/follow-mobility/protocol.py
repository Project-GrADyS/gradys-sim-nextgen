from gradys.protocol.addons.follow_mobility import MobilityFollower, MobilityLeader
from gradys.protocol.addons.random_mobility import RandomMobilityAddon
from gradys.protocol.interface import IProtocol
from gradys.protocol.messages.telemetry import Telemetry


class FollowerProtocol(IProtocol):
    follower: MobilityFollower

    def initialize(self, stage: int) -> None:
        self.follower = MobilityFollower(self)
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
        MobilityLeader(self)
        random = RandomMobilityAddon(self)
        random.initiate_random_trip()

    def handle_timer(self, timer: str) -> None:
        pass

    def handle_packet(self, message: str) -> None:
        pass

    def handle_telemetry(self, telemetry: Telemetry) -> None:
        pass

    def finish(self) -> None:
        pass