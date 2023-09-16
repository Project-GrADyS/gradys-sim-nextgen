import random
from simulator.messages.communication import SendMessageCommand
from simulator.messages.telemetry import Telemetry
from simulator.protocols import IProtocol
from simulator.protocols.simple.message import SimpleMessage, SenderType
from simulator.provider import IProvider


class SimpleProtocolSensor(IProtocol):
    packets: int

    def initialize(self, stage: int):   
        self.packets = 5
        self.provider.tracked_variables["packets"] = self.packets
        self.provider.schedule_timer({}, self.provider.current_time() + random.random())

    def handle_timer(self, timer: dict):
        self.packets += 1
        self.provider.tracked_variables["packets"] = self.packets
        self.provider.schedule_timer({}, self.provider.current_time() + 2)

    def handle_packet(self, message: SimpleMessage):
        print(f"SimpleProtocolSensor packets: {self.packets}, {message['sender']}")
        if message['sender'] == SenderType.DRONE:
            print(f"SimpleProtocolSensor packets2: {self.packets}")
            response: SimpleMessage = {
                'sender': SenderType.SENSOR.name,
                'content': self.packets
            }
            self.provider.send_communication_command(SendMessageCommand(response))
            self.packets = 0
            self.provider.tracked_variables["packets"] = self.packets

    def handle_telemetry(self, telemetry: Telemetry):
        pass

    def finish(self):
        pass
