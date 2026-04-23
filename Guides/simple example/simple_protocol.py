import enum
import json
import logging
from typing import TypedDict

from gradysim.protocol.interface import IProtocol
from gradysim.protocol.messages.communication import SendMessageCommand, BroadcastMessageCommand
from gradysim.protocol.messages.telemetry import Telemetry
from gradysim.protocol.plugin.mission_mobility import MissionMobilityPlugin, MissionMobilityConfiguration, LoopMission



class SimpleSender(enum.Enum):
    SENSOR = 0
    UAV = 1
    GROUND_STATION = 2


class SimpleMessage(TypedDict):
    packet_count: int
    sender_type: int
    sender: int


def report_message(message: SimpleMessage) -> str:
    return (f"Received message with {message['packet_count']} packets from "
            f"{SimpleSender(message['sender_type']).name} {message['sender']}")


class SimpleSensorProtocol(IProtocol):
    _log: logging.Logger
    packet_count: int

    def initialize(self) -> None:
        self._log = logging.getLogger()
        self.packet_count = 0

        self._generate_packet()

    def _generate_packet(self) -> None:
        self.packet_count += 1
        self._log.info(f"Generated packet, current count {self.packet_count}")
        self.provider.schedule_timer("", self.provider.current_time() + 1)

    def handle_timer(self, timer: str) -> None:
        self._generate_packet()

    def handle_packet(self, message: str) -> None:
        simple_message: SimpleMessage = json.loads(message)
        self._log.info(report_message(simple_message))

        if simple_message['sender_type'] == SimpleSender.UAV.value:
            response: SimpleMessage = {
                'packet_count': self.packet_count,
                'sender_type': SimpleSender.SENSOR.value,
                'sender': self.provider.get_id()
            }

            command = SendMessageCommand(json.dumps(response), simple_message['sender'])
            self.provider.send_communication_command(command)

            self._log.info(f"Sent {response['packet_count']} packets to UAV {simple_message['sender']}")

            self.packet_count = 0

    def handle_telemetry(self, telemetry: Telemetry) -> None:
        pass

    def finish(self) -> None:
        self._log.info(f"Final packet count: {self.packet_count}")


mission_list = [
    [
        (0, 0, 20),
        (150, 0, 20)
    ],
    [
        (0, 0, 20),
        (0, 150, 20)
    ],
    [
        (0, 0, 20),
        (-150, 0, 20)
    ],
    [
        (0, 0, 20),
        (0, -150, 20)
    ]
]


class SimpleUAVProtocol(IProtocol):
    _log: logging.Logger

    packet_count: int

    _mission: MissionMobilityPlugin

    def initialize(self) -> None:
        self._log = logging.getLogger()
        self.packet_count = 0

        self._mission = MissionMobilityPlugin(self, MissionMobilityConfiguration(
            loop_mission=LoopMission.REVERSE,
        ))

        self._mission.start_mission(mission_list.pop())

        self._send_heartbeat()

    def _send_heartbeat(self) -> None:
        self._log.info(f"Sending heartbeat, current count {self.packet_count}")

        message: SimpleMessage = {
            'packet_count': self.packet_count,
            'sender_type': SimpleSender.UAV.value,
            'sender': self.provider.get_id()
        }
        command = BroadcastMessageCommand(json.dumps(message))
        self.provider.send_communication_command(command)

        self.provider.schedule_timer("", self.provider.current_time() + 1)

    def handle_timer(self, timer: str) -> None:
        self._send_heartbeat()

    def handle_packet(self, message: str) -> None:
        simple_message: SimpleMessage = json.loads(message)
        self._log.info(report_message(simple_message))

        if simple_message['sender_type'] == SimpleSender.SENSOR.value:
            self.packet_count += simple_message['packet_count']
            self._log.info(f"Received {simple_message['packet_count']} packets from "
                           f"sensor {simple_message['sender']}. Current count {self.packet_count}")
        elif simple_message['sender_type'] == SimpleSender.GROUND_STATION.value:
            self._log.info("Received acknowledgment from ground station")
            self.packet_count = 0

    def handle_telemetry(self, telemetry: Telemetry) -> None:
        pass

    def finish(self) -> None:
        self._log.info(f"Final packet count: {self.packet_count}")


class SimpleGroundStationProtocol(IProtocol):
    _log: logging.Logger
    packet_count: int

    def initialize(self) -> None:
        self._log = logging.getLogger()
        self.packet_count = 0

    def handle_timer(self, timer: str) -> None:
        pass

    def handle_packet(self, message: str) -> None:
        simple_message: SimpleMessage = json.loads(message)
        self._log.info(report_message(simple_message))

        if simple_message['sender_type'] == SimpleSender.UAV.value:
            response: SimpleMessage = {
                'packet_count': self.packet_count,
                'sender_type': SimpleSender.GROUND_STATION.value,
                'sender': self.provider.get_id()
            }

            command = SendMessageCommand(json.dumps(response), simple_message['sender'])
            self.provider.send_communication_command(command)

            self.packet_count += simple_message['packet_count']
            self._log.info(f"Sent acknowledgment to UAV {simple_message['sender']}. Current count {self.packet_count}")

    def handle_telemetry(self, telemetry: Telemetry) -> None:
        pass

    def finish(self) -> None:
        self._log.info(f"Final packet count: {self.packet_count}")
