import logging

from gradysim.protocol.interface import IProtocol
from gradysim.simulator import SIMULATION_LOGGER
from gradysim.protocol.messages.telemetry import Telemetry


class CounterProtocol(IProtocol):
    counter: int

    def initialize(self, stage):
        # We initialize our counter at zero
        self.counter = 0

        # Using the protocol's provider to schedule a timer
        self.provider.schedule_timer(
            "",  # We don't care about the name since we're only going to use one
            self.provider.current_time() + 1  # Scheduling it 1 second from now
        )

    def handle_timer(self, timer: str):
        # Every time the timer fires we increment the counter
        self.counter += 1

        # And schedule a new one
        self.provider.schedule_timer(
            "",
            self.provider.current_time() + 1
        )

    def handle_packet(self, message: str):
        # We won't be receiving packets, so we don't care about this
        pass

    def handle_telemetry(self, telemetry: Telemetry):
        # We don't care about mobility, so we are ignoring the received telemetry
        pass

    def finish(self):
        # We print our final counter value at the end of the simulator
        logger = logging.getLogger(SIMULATION_LOGGER)
        logger.info(f"Final counter value: {self.counter}")
