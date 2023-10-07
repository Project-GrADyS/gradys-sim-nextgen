from simulator.messages.communication import CommunicationCommand
from simulator.messages.mobility import MobilityCommand
from simulator.node.handler.mobility import MobilityHandler
from simulator.node.node import Node
from simulator.node.handler.communication import CommunicationHandler
from simulator.node.handler.timer import TimerHandler
from simulator.provider.interface import IProvider


class PythonProvider(IProvider):
    def __init__(self, node: Node, communication_handler: CommunicationHandler, timer_handler: TimerHandler, mobility_handler: MobilityHandler):
        self.node = node
        self.communication_handler = communication_handler
        self.timer_handler = timer_handler
        self.mobility_handler = mobility_handler

    def send_communication_command(self, command: CommunicationCommand):
        self.communication_handler.handle_command(command, self.node)

    def send_mobility_command(self, command: MobilityCommand):
        self.mobility_handler.handle_command(command, self.node)

    def schedule_timer(self, timer: str, timestamp: float):
        self.timer_handler.set_timer(timer, timestamp, self.node)

    def current_time(self) -> float:
        return self.timer_handler.get_current_time()