import logging
import random
from gradysim.protocol.addons.mission_mobility import (
    LoopMission,
    MissionMobilityAddon,
    MissionMobilityConfiguration,
)
from gradysim.protocol.messages.communication import BroadcastMessageCommand, SendMessageCommand
from gradysim.protocol.messages.mobility import GotoCoordsMobilityCommand

from gradysim.protocol.messages.telemetry import Telemetry
from gradysim.protocol.interface import IProtocol
from message import ZigZagMessage, ZigZagMessageType
from utils import CommunicationStatus
from gradysim.simulator.log import SIMULATION_LOGGER


class ZigZagProtocolMobile(IProtocol):
    def __init__(self):
        self.timeout_end: int = 0
        self.timeout_set: bool = False
        self.timeout_duration: int = 5
        self.communication_status: CommunicationStatus = CommunicationStatus.FREE
        self.tentative_target: int = -1
        self.last_target: int = -1
        self.current_data_load: int = 0
        self.stable_data_load: int = self.current_data_load
        self.current_telemetry: Telemetry
        self.last_stable_telemetry: Telemetry
        self.last_payload: ZigZagMessage = ZigZagMessage()
        self._logger = logging.getLogger(SIMULATION_LOGGER)

    def initialize(self):
        self.provider.tracked_variables["current_data_load"] = self.current_data_load

        self.mission: MissionMobilityAddon = MissionMobilityAddon(
            self, MissionMobilityConfiguration(loop_mission=LoopMission.REVERSE)
        )

        self.mission.start_mission([(20, 20, 5), (20, -20, 5), (-20, -20, 5), (-20, 20, 5)])

        self._update_payload()
        self.provider.schedule_timer("", self.provider.current_time() + 1)

    def handle_timer(self, timer: str):
        
        if (
            not self._is_timedout()
            and self.communication_status == CommunicationStatus.FREE
        ):
            self._update_payload()
        
        self.provider.schedule_timer("", self.provider.current_time() + 1)


    def handle_packet(self, message: str):
        message: ZigZagMessage = ZigZagMessage.from_json(message)

        match message.message_type:
            case ZigZagMessageType.HEARTBEAT:
                if self._is_timedout() and self.last_target != message.source_id and self.tentative_target != message.source_id:
                    self._reset_parameters()

                if self.communication_status == CommunicationStatus.COLLECTING:
                    self._reset_parameters()

                if not self._is_timedout():
                    self.tentative_target = message.source_id
                    self._initiate_timeout()
                    self.communication_status = CommunicationStatus.REQUESTING

            case ZigZagMessageType.PAIR_REQUEST:
                if message.destination_id != self.provider.get_id():
                    return

                if self.communication_status == CommunicationStatus.COLLECTING:
                    self._reset_parameters()

                if self._is_timedout():
                    if message.source_id == self.tentative_target:
                        self.communication_status = CommunicationStatus.PAIRED
                else: 
                    self.tentative_target = message.source_id
                    self._initiate_timeout()
                    self.communication_status = CommunicationStatus.PAIRED
            
            case ZigZagMessageType.PAIR_CONFIRM:
                if message.source_id == self.tentative_target and message.destination_id == self.provider.get_id():
                    if self.communication_status != CommunicationStatus.PAIRED_FINISHED:
                        if self.mission.is_reversed != message.reversed_flag or self.provider.get_id() > message.source_id:
                            reversed = not self.mission.is_reversed
                            self.mission.set_reversed(reversed = reversed)
                            
                            self.current_data_load = self.current_data_load + message.data_length
                            self.provider.tracked_variables["current_data_load"] = self.current_data_load
                    self.communication_status = CommunicationStatus.PAIRED_FINISHED

            case ZigZagMessageType.BEARER:
                if not self._is_timedout() and self.communication_status == CommunicationStatus.FREE:
                    self.current_data_load = self.current_data_load + message.data_length
                    self.stable_data_load = self.current_data_load
                    self.provider.tracked_variables["current_data_load"] = self.current_data_load
                    self._initiate_timeout()
                    self.communication_status = CommunicationStatus.COLLECTING
        
        self._update_payload()

    def handle_telemetry(self, telemetry: Telemetry):
        self.current_telemetry = telemetry

        if self._is_timedout():
            self.last_stable_telemetry = telemetry

    def finish(self):
        pass

    def _update_payload(self):
        message = ZigZagMessage(
            source_id=self.provider.get_id(),
            reversed_flag=self.mission.is_reversed,
        )

        if self.provider.get_id() == self.tentative_target:
            return

        match self.communication_status:
            case CommunicationStatus.FREE:
                message.message_type = ZigZagMessageType.HEARTBEAT

            case CommunicationStatus.REQUESTING:
                message.message_type = ZigZagMessageType.PAIR_REQUEST
                message.destination_id = self.tentative_target

            case CommunicationStatus.PAIRED | CommunicationStatus.PAIRED_FINISHED:
                message.message_type = ZigZagMessageType.PAIR_CONFIRM
                message.destination_id = self.tentative_target
                message.data_length = self.stable_data_load

            case CommunicationStatus.COLLECTING:
                pass

        if (
            message.message_type != self.last_payload.message_type
            or message.source_id != self.last_payload.source_id
            or message.destination_id != self.last_payload.destination_id
            or message.reversed_flag != self.last_payload.reversed_flag
        ):
            self.last_payload = message

            if self.tentative_target < 0:
                command = BroadcastMessageCommand(
                    message=message.to_json()
                )

            else:
                command = SendMessageCommand(
                    message=message.to_json(), destination=self.tentative_target
                )
  
            self.provider.send_communication_command(command)
           
    def _initiate_timeout(self):
        if self.timeout_duration > 0:
            self.timeout_end = self.provider.current_time() + self.timeout_duration
            self.timeout_set = True

    def _is_timedout(self):
        def __is_timedout():
            if self.timeout_set:
                if self.provider.current_time() < self.timeout_end:
                    return True
                else:
                    self.timeout_set = False
                    return False
            else:
                return False

        old_timeout_set = self.timeout_set
        is_timedout = __is_timedout()
        if not is_timedout and old_timeout_set:
            self._reset_parameters()
        return is_timedout

    def _reset_parameters(self):
        self.timeout_set = False
        self.last_target = self.tentative_target
        self.tentative_target = -1
        self.communication_status = CommunicationStatus.FREE
        self.last_stable_telemetry = self.current_telemetry
        self.stable_data_load = self.current_data_load
        self._update_payload()
