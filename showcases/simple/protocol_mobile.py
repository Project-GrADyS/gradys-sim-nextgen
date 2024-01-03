import logging
import random
from gradysim.protocol.plugin.mission_mobility import (
    LoopMission,
    MissionMobilityPlugin,
    MissionMobilityConfiguration,
)
from gradysim.protocol.plugin.statistics import create_statistics, finish_statistics
from gradysim.protocol.messages.communication import BroadcastMessageCommand

from gradysim.protocol.messages.telemetry import Telemetry
from gradysim.protocol.interface import IProtocol
from message import SimpleMessage, SenderType


class SimpleProtocolMobile(IProtocol):
    def __init__(self):
        self.packets: int = 0
        self.last_telemetry_message: Telemetry

        self._logger = logging.getLogger()

    def initialize(self):
        self._logger.debug("Initializing mobile protocol")

        create_statistics(self)

        self.mission: MissionMobilityPlugin= MissionMobilityPlugin(
            self, MissionMobilityConfiguration(loop_mission=LoopMission.RESTART)
        )

        self.mission.start_mission(
            mission=[(20, 20, 5), (20, -20, 5), (-20, -20, 5), (-20, 20, 5)]
        )

        # Scheduling self message with a random delay to prevent collision when sending pings
        self.provider.tracked_variables["packets"] = self.packets
        self.provider.schedule_timer("", self.provider.current_time() + random.random())

    def handle_timer(self, timer: str):
        ping = SimpleMessage(sender=SenderType.DRONE, content=self.packets)

        self.provider.send_communication_command(
            BroadcastMessageCommand(ping.to_json())
        )

        self.provider.schedule_timer("", self.provider.current_time() + random.random())

    def handle_packet(self, message: str):
        message: SimpleMessage = SimpleMessage.from_json(message)
        self._logger.debug(
            f"SimpleProtocolMobile received packet: {self.packets}, {message.sender}"
        )

        if message.sender == SenderType.GROUND_STATION:
            self.packets = 0
            self.provider.tracked_variables["packets"] = self.packets

            if self.mission.is_reversed:
                reversed = not self.mission.is_reversed
                self.mission.set_reversed(reversed=reversed)

        elif message.sender == SenderType.SENSOR:
            self.packets += message.content
            self.provider.tracked_variables["packets"] = self.packets

    def handle_telemetry(self, telemetry: Telemetry):
        self.last_telemetry_message = telemetry

    def finish(self):
        finish_statistics(self)
