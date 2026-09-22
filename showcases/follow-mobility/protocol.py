import logging
import math
from typing import Optional

from gradysim.protocol.plugin.follow_mobility import (
    MobilityFollowerPlugin,
    MobilityFollowerConfiguration,
    MobilityLeaderPlugin,
    MobilityLeaderConfiguration,
)
from gradysim.protocol.plugin.mission_mobility import MissionMobilityPlugin, MissionMobilityConfiguration, LoopMission
from gradysim.protocol.interface import IProtocol
from gradysim.protocol.messages.mobility import SetSpeedMobilityCommand
from gradysim.protocol.messages.telemetry import Telemetry
from gradysim.protocol.position import Position

# V-formation offsets: followers spread behind and to the sides of the leader.
# These are relative positions in the leader's local frame when follow_orientation=True.
FORMATION_OFFSETS: list[Position] = [
    (-5, -5, 0),
    (-5,  5, 0),
    (-10, -10, 0),
    (-10,  10, 0),
    (-15, -5, 0),
    (-15,  5, 0),
    (-20, -10, 0),
    (-20,  10, 0),
    (-25, -5, 0),
    (-25,  5, 0),
]


class FollowerProtocol(IProtocol):
    follower: MobilityFollowerPlugin

    def __init__(self):
        self._logger = logging.getLogger()

    def initialize(self) -> None:
        self.follower = MobilityFollowerPlugin(
            self,
            MobilityFollowerConfiguration(
                follow_orientation=True,
            ),
        )

        # Pick a formation offset based on this node's ID (node 0 is the leader)
        follower_index = self.provider.get_id() - 1
        if 0 <= follower_index < len(FORMATION_OFFSETS):
            self.follower.set_relative_position(FORMATION_OFFSETS[follower_index])

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
    _previous_position: Optional[Position] = None

    def __init__(self):
        self._logger = logging.getLogger()

    def initialize(self) -> None:
        self.leader = MobilityLeaderPlugin(self, MobilityLeaderConfiguration(
            initial_orientation=0.0,
        ))

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
        self._logger.info(f"Being followed by: {self.leader.followers} "
                          f"| orientation: {self.leader.orientation:.1f}°")

        self.provider.schedule_timer("", self.provider.current_time() + 1)

    def handle_packet(self, message: str) -> None:
        pass

    def handle_telemetry(self, telemetry: Telemetry) -> None:
        current = telemetry.current_position

        if self._previous_position is not None:
            dx = current[0] - self._previous_position[0]
            dy = current[1] - self._previous_position[1]

            # Only update orientation when there is meaningful movement
            if dx * dx + dy * dy > 1e-6:
                angle = math.degrees(math.atan2(dy, dx))
                self.leader.set_orientation(angle)

        self._previous_position = current

    def finish(self) -> None:
        pass

