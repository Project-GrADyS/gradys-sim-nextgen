import random
from enum import Enum
from simulator.protocols.IProtocol import IProtocol
from simulator.messages.CommunicationCommand import SendMessageCommand
from simulator.messages.MobilityCommand import (
    SetModeCommand,
    MobilityMode,
    ReverseCommand,
)
from simulator.messages.Telemetry import Telemetry
from simulator.protocols.zigzag.ZigzagMessage import ZigzagMessageType, ZigzagMessage


class CommunicationStatus(int, Enum):
    FREE = 0
    REQUESTING = 1
    PAIRED = 2
    COLLECTING = 3
    PAIRED_FINISHED = 4


class ZigzagProtocolMobile(IProtocol):
    timeout_set: bool = False
    timeout_end: int = 0
    timeout_duration: int = 0
    communication_status: CommunicationStatus = CommunicationStatus.FREE
    tentative_target: int = -1
    last_target: int = -1
    tentative_target_name: str = ""
    current_data_load: int = 0
    stable_data_load: int = current_data_load
    current_telemetry = Telemetry()
    last_stable_telemetry = Telemetry()
    last_payload: ZigzagMessage = ZigzagMessage()

    def initialize(self, stage: int):
        if stage == 0:
            self.timeout_duration = 1
            self.update_payload()

    def handle_telemetry(self, telemetry: Telemetry):
        self.current_telemetry = telemetry
        if not self._is_timedout():
            self.last_stable_telemetry = telemetry
        self.update_payload()

    def handle_timer(self, timer: dict):
        # ping = SimpleMessage(sender=SenderType.DRONE, content=self.packets)
        # self.provider.send_communication_command(SendMessageCommand(ping.to_json()))
        self.provider.schedule_timer({}, self.provider.current_time() + 2)

    def handle_packet(self, message: str):
        print(
            f"ZigzagMessage received packet: {message}"
        ) 
        message: ZigzagMessage = ZigzagMessage.from_json(message)
       
        if message is not None:
            destination_is_groundstation = message.nextWaypointID == -1
            if (
                self.current_telemetry.current_command != -1
                and not destination_is_groundstation
            ):
                return

            if self.is_timedout() and self.last_target != payload.source_id and self.tentative_target != payload.source_id:
                self.reset_parameters()

            if self.communication_status == CommunicationStatus.COLLECTING:
                self.reset_parameters()

            if not self.is_timedout():
                if (
                    self.last_stable_telemetry.next_waypoint_id == payload.next_waypoint_id
                    or self.last_stable_telemetry.next_waypoint_id == payload.last_waypoint_id
                    or self.last_stable_telemetry.next_waypoint_id == -1
                    or payload.next_waypoint_id == -1
                ):
                    self.tentative_target = payload.source_id
                    self.tentative_target_name = packet
                    self.initiate_timeout(self.timeout_duration)
                    self.communication_status = CommunicationStatus.REQUESTING
                    print(
                        f"{self.get_parent_module().get_id()} received heartbeat from {self.tentative_target}"
                    )

            if payload.message_type == ZigzagMessageType.HEARTBEAT:
                if self.is_timedout() and self.last_target != payload.source_id and self.tentative_target != payload.source_id:
                    self.reset_parameters()

                if self.communication_status == CommunicationStatus.COLLECTING:
                    self.reset_parameters()

                if not self.is_timedout():
                    if (
                        self.last_stable_telemetry.next_waypoint_id == payload.next_waypoint_id
                        or self.last_stable_telemetry.next_waypoint_id == payload.last_waypoint_id
                        or self.last_stable_telemetry.next_waypoint_id == -1
                        or payload.next_waypoint_id == -1
                    ):
                        self.tentative_target = payload.source_id
                        self.tentative_target_name = packet
                        self.initiate_timeout(self.timeout_duration)
                        self.communication_status = CommunicationStatus.REQUESTING
                        print(
                            f"{self.get_parent_module().get_id()} received heartbeat from {self.tentative_target}"
                        )

            # Handle other message types similarly


        if message.sender == SenderType.GROUND_STATION:
            self.packets = 0
            self.provider.tracked_variables["packets"] = self.packets

            if self.last_telemetry_message.is_reversed:
                self.provider.send_mobility_command(ReverseCommand())

        elif message.sender == SenderType.SENSOR:
            self.packets += message.content
            self.provider.tracked_variables["packets"] = self.packets



    def finish(self):
        pass
    
    def _is_timedout(self):
        old_value = self.timeout_set
        value = self.is_timedout()
        if not value and old_value:
            self.reset_parameters()
        return value
       
    def reset_parameters(self):
        self.timeout_set = False
        self.last_target = self.tentative_target
        self.tentative_target = -1
        self.tentative_target_name = ""
        self.set_target("")
        self.communication_status = CommunicationStatus.FREE
        self.last_stable_telemetry = self.current_telemetry
        self.stable_data_load = self.current_data_load
        self.update_payload()


    def is_timedout(self) -> bool:
        if self.timeout_set:
            if self.provider.current_time < self.timeout_end:
                return True
            else:
                self.timeout_set = False
                return False
        else:
            return False
    
    def initiate_timeout(self, duration: int) -> None:
        if duration > 0:
            self.timeout_end = self.provider.current_time + duration
            self.timeout_set = True
