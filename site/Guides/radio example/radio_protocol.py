from __future__ import annotations

import logging
from typing import List

from gradysim.protocol.interface import IProtocol
from gradysim.protocol.messages.telemetry import Telemetry
from gradysim.protocol.messages.communication import (
    CommunicationCommand,
    CommunicationCommandType,
)
from gradysim.simulator.extension.radio import Radio


class RadioProtocol(IProtocol):
    """
    Demo protocol that instantiates two radios with different ranges and sends a few messages
    during initialization. It also collects any received messages for display on finish().
    """

    def __init__(self) -> None:
        self.received: List[str] = []
        self.short_radio: Radio | None = None
        self.long_radio: Radio | None = None
        self._logger = logging.getLogger()

    def initialize(self) -> None:
        # Two radios with distinct characteristics
        self.short_radio = Radio(self)
        self.long_radio = Radio(self)

        self.short_radio.set_configuration(transmission_range=10)
        self.long_radio.set_configuration(transmission_range=100)

        # Only node 0 performs the demo transmissions
        if self.provider.get_id() == 0:
            # 1) Short-range broadcast: only nearby nodes (<=10 m) receive it
            self.short_radio.send_communication_command(
                CommunicationCommand(
                    command_type=CommunicationCommandType.BROADCAST,
                    message="hello_short",
                )
            )

            # 2) Long-range unicast to node 2 (50 m away)
            self.long_radio.send_communication_command(
                CommunicationCommand(
                    command_type=CommunicationCommandType.SEND,
                    message="ping_long",
                    destination=2,
                )
            )

            # 3) Direct provider send uses the handler's default medium (range=60 m)
            self.provider.send_communication_command(
                CommunicationCommand(
                    command_type=CommunicationCommandType.SEND,
                    message="via_provider",
                    destination=2,
                )
            )

    def handle_timer(self, timer: str) -> None:
        pass

    def handle_packet(self, message: str) -> None:
        self.received.append(message)

    def handle_telemetry(self, telemetry: Telemetry) -> None:
        pass

    def finish(self) -> None:
        node_id = self.provider.get_id()
        ordered = sorted(self.received)
        self._logger.info(f"Node {node_id} received: {ordered}")
