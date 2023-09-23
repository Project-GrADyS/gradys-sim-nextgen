from typing import Dict, TypedDict

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


class Medium(TypedDict):
    transmission_range: float


def can_transmit(source_position: Position, destination_position: Position, communication_medium: Medium):
    squared_distance = (destination_position[0] - source_position[0]) ** 2 + \
                       (destination_position[1] - source_position[1]) ** 2 + \
                       (destination_position[2] - source_position[2]) ** 2
    return squared_distance <= (communication_medium['transmission_range'] * communication_medium['transmission_range'])


class CommunicationHandler(INodeHandler):
    sources: Dict[int, CommunicationSource]
    destinations: Dict[int, CommunicationDestination]

    def __init__(self, communication_medium: Medium):
        self.sources = {}
        self.destinations = {}
        self.communication_medium = communication_medium

    def register_node(self, node: Node):
        self.sources[node.id] = CommunicationSource(node)
        self.destinations[node.id] = CommunicationDestination(node)

    def handle_command(self, command:  CommunicationCommand, sender: Node):
        if sender.id == command.destination:
            raise CommunicationException("Error transmitting message: message destination is equal to sender. Try "
                                         "using schedule_timer.")

        source = self.sources[sender.id]

        if command.type == CommunicationCommandType.BROADCAST:
            for destination, endpoint in self.destinations.items():
                if destination != sender.id:
                    self._transmit_message(command.message, source, endpoint)
        else:
            destination = command.destination
            if destination is None:
                raise CommunicationException("Error transmitting message: a destination is "
                                             "required when command type SEND is used.")
            if destination not in self.destinations:
                raise CommunicationException(f"Error transmitting message: destination {destination} does not exist.")

            self._transmit_message(command.message, source, self.destinations[destination])

    def _transmit_message(self, message: str, source: CommunicationSource, destination: CommunicationDestination):
        if can_transmit(source.node.position, destination.node.position, self.communication_medium):
            destination.receive_message(message, source)
