import logging
import random

from gradysim.protocol.plugin.follow_mobility import MobilityFollowerPlugin, MobilityLeaderPlugin
from gradysim.protocol.plugin.mission_mobility import MissionMobilityPlugin, MissionMobilityConfiguration, LoopMission
from gradysim.protocol.interface import IProtocol
from gradysim.protocol.messages.mobility import SetSpeedMobilityCommand
from gradysim.protocol.messages.telemetry import Telemetry


class FollowerProtocol(IProtocol):
    follower: MobilityFollowerPlugin

    def __init__(self):
        self._logger = logging.getLogger()

    def initialize(self) -> None:
        self.follower = MobilityFollowerPlugin(self)

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
    leader: MobilityLeaderPlugin

    def __init__(self):
        self._logger = logging.getLogger()

    def initialize(self) -> None:
        self.leader = MobilityLeaderPlugin(self)

        mission = MissionMobilityPlugin(self, MissionMobilityConfiguration(loop_mission=LoopMission.RESTART))
        mission.start_mission([
            (20, 20, 5),
            (20, -20, 5),
            (-20, -20, 5),
            (-20, 20, 5)
        ])

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
