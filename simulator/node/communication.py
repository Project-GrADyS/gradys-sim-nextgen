from typing import Dict

from simulator.event import EventLoop
from simulator.messages.communication import CommunicationCommand, CommunicationCommandType
from simulator.node import Node, Position
from simulator.node.interface import INodeHandler


class CommunicationDestination:
    node: Node

    def __init__(self, node: Node):
        self.node = node

    def receive_message(self, message: str, source: 'CommunicationSource'):
        self.node.protocol_encapsulator.handle_packet(message)


class CommunicationSource:
    node: Node

    def __init__(self, node: Node):
        self.node = node

    def send_message(self, message: str, endpoint: CommunicationDestination):
        endpoint.receive_message(message, self)


class CommunicationException(Exception):
    pass


class Medium:
    transmission_range: float
    delay: float

    def __init__(self, transmission_range: float = 60, delay: float = 0):
        self.transmission_range = transmission_range
        self.delay = delay


def can_transmit(source_position: Position, destination_position: Position, communication_medium: Medium):
    squared_distance = (destination_position[0] - source_position[0]) ** 2 + \
                       (destination_position[1] - source_position[1]) ** 2 + \
                       (destination_position[2] - source_position[2]) ** 2
    return squared_distance <= (communication_medium.transmission_range * communication_medium.transmission_range)


class CommunicationHandler(INodeHandler):
    _sources: Dict[int, CommunicationSource]
    _destinations: Dict[int, CommunicationDestination]
    _event_loop: EventLoop

    def __init__(self, communication_medium: Medium):
        self._injected = False

        self._sources = {}
        self._destinations = {}
        self.communication_medium = communication_medium

    def inject(self, event_loop: EventLoop):
        self._injected = True
        self._event_loop = event_loop

    def register_node(self, node: Node):
        if not self._injected:
            raise CommunicationException("Error registering node: Cannot register node on uninitialized "
                                         "node handler")
        self._sources[node.id] = CommunicationSource(node)
        self._destinations[node.id] = CommunicationDestination(node)

    def handle_command(self, command:  CommunicationCommand, sender: Node):
        """
        Performs a communication command
        :param command: Command being issued
        :param sender: Node issuing the command
        """
        if sender.id == command.destination:
            raise CommunicationException("Error transmitting message: message destination is equal to sender. Try "
                                         "using schedule_timer.")

        source = self._sources[sender.id]

        if command.type == CommunicationCommandType.BROADCAST:
            for destination, endpoint in self._destinations.items():
                if destination != sender.id:
                    self._transmit_message(command.message, source, endpoint)
        else:
            destination = command.destination
            if destination is None:
                raise CommunicationException("Error transmitting message: a destination is "
                                             "required when command type SEND is used.")
            if destination not in self._destinations:
                raise CommunicationException(f"Error transmitting message: destination {destination} does not exist.")

            self._transmit_message(command.message, source, self._destinations[destination])

    def _transmit_message(self, message: str, source: CommunicationSource, destination: CommunicationDestination):
        if can_transmit(source.node.position, destination.node.position, self.communication_medium):
            if self.communication_medium.delay <= 0:
                destination.receive_message(message, source)
            else:
                self._event_loop.schedule_event(
                    self._event_loop.current_time + self.communication_medium.delay,
                    lambda: destination.receive_message(message, source)
                )
