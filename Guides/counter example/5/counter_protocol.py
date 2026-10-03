import logging
import random

from gradysim.protocol.interface import IProtocol
from gradysim.protocol.messages.communication import BroadcastMessageCommand
from gradysim.protocol.messages.mobility import GotoCoordsMobilityCommand
from gradysim.protocol.messages.telemetry import Telemetry
from gradysim.simulator.extension.visualization_controller import VisualizationController


class CounterProtocol(IProtocol):
    sent: int
    received: int

    visualization_controller: VisualizationController

    def initialize(self):
        # We initialize two counters: one for sent and one
        # for received messages
        self.sent = 0
        self.received = 0

        # Using the protocol's provider to schedule a timer
        self.provider.schedule_timer(
            "message",  # We don't care about the name since we're only going to use one
            self.provider.current_time() + 1  # Scheduling it 1 second from now
        )

        self.provider.schedule_timer(
            "mobility",  # We don't care about the name since we're only going to use one
            self.provider.current_time() + 5  # Scheduling it 1 second from now
        )

        self.visualization_controller = VisualizationController()

        # The node will start painted black
        self.visualization_controller.paint_node(self.provider.get_id(), (0, 0, 0))

    def handle_timer(self, timer: str):
        if timer == "message":
            # Every time the timer fires we increment the counter
            self.sent += 1

            # Creating a new communication command that will instruct the mobility module
            # to broadcast a message
            command = BroadcastMessageCommand(
                message=""  # Content is irrelevant, we are only counting messages
            )

            # Sending the command
            self.provider.send_communication_command(command)

            # Scheduling a new timer
            self.provider.schedule_timer(
                "message",
                self.provider.current_time() + 1
            )
        else:
            # Issuing a GOTO_COORDS command. Mobility commands have dynamic parameters
            # so subclasses are provided for every command type to help you create them
            # with proper typing support
            command = GotoCoordsMobilityCommand(
                random.uniform(-50, 50),
                random.uniform(-50, 50),
                random.uniform(0, 50)
            )
            self.provider.send_mobility_command(command)

            # Scheduling a new timer
            self.provider.schedule_timer(
                "mobility",
                self.provider.current_time() + 5
            )

    def handle_packet(self, message: str):
        # This time we care about received messages, we increment our received
        # counter every time a new one arrives.
        self.received += 1

        # The node progressively changes its color to red as it receives more messages
        self.visualization_controller.paint_node(self.provider.get_id(), (min(self.received, 255), 0, 0))

    def handle_telemetry(self, telemetry: Telemetry):
        # We don't care about mobility, so we are ignoring the received telemetry
        pass

    def finish(self):
        # We print our final counter value at the end of the simulator
        logging.info(f"Final counter values: "
                     f"sent={self.sent} ; received={self.received}")
