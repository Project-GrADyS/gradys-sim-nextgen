import math
from dataclasses import dataclass
from typing import Dict

from gradysim.simulator.event import EventLoop
from gradysim.protocol.messages.mobility import MobilityCommand, MobilityCommandType
from gradysim.protocol.messages.telemetry import Telemetry
from gradysim.simulator.node import Node
from gradysim.simulator.position import Position
from gradysim.simulator.handler.interface import INodeHandler


class MobilityException(Exception):
    pass


@dataclass
class MobilityConfiguration:
    """
    Configuration class for the mobility handler
    """

    update_rate: float = 0.01
    """Interval in simulation seconds between mobility updates"""

    default_speed: float = 10
    """This is the default speed of a node in m/s"""


class MobilityHandler(INodeHandler):
    """
    Introduces mobility into the simulatuon. Works by registering a regular event that
    updates every node's position based on it's target and speed. A node, through it's provider,
    can sent this handler communication commands to alter it's behaviour including it's speed 
    and current target. Nodes also recieve telemetry updates containing information pertaining
    a node's current mobility status.
    """

    @staticmethod
    def get_label() -> str:
        return "mobility"

    _event_loop: EventLoop

    _nodes: Dict[int, Node]
    _targets: Dict[int, Position]
    _speeds: Dict[int, float]

    def __init__(self, configuration: MobilityConfiguration = MobilityConfiguration()):
        """
        Constructor for the mobility handler

        Args:
            configuration: Configuration for the mobility handler. If not set all default values will be used.
        """
        self._configuration = configuration
        self._nodes = {}
        self._targets = {}
        self._speeds = {}
        self._injected = False

    def inject(self, event_loop: EventLoop):
        self._injected = True
        self._event_loop = event_loop

        event_loop.schedule_event(event_loop.current_time + self._configuration.update_rate,
                                  self._update_movement,
                                  "Mobility")

    def register_node(self, node: Node):
        if not self._injected:
            raise MobilityException("Error registering node: cannot register nodes while mobility handler "
                                    "is uninitialized.")

        self._nodes[node.id] = node
        self._speeds[node.id] = self._configuration.default_speed

    def _update_movement(self):
        for node_id in self._nodes.keys():
            node = self._nodes[node_id]

            # If the node has a target update its position
            if node_id in self._targets:
                target = self._targets[node_id]
                current_position = node.position
                speed = self._speeds[node_id]
                target_vector: Position = (target[0] - current_position[0],
                                           target[1] - current_position[1],
                                           target[2] - current_position[2])
                movement_multiplier = speed * self._configuration.update_rate
                distance_delta = math.sqrt(target_vector[0] ** 2 + target_vector[1] ** 2 + target_vector[2] ** 2)

                if movement_multiplier >= distance_delta:
                    node.position = (
                        target[0],
                        target[1],
                        target[2]
                    )
                else:
                    target_vector_multiplier = movement_multiplier / distance_delta

                    node.position = (
                        current_position[0] + target_vector[0] * target_vector_multiplier,
                        current_position[1] + target_vector[1] * target_vector_multiplier,
                        current_position[2] + target_vector[2] * target_vector_multiplier
                    )
            telemetry = Telemetry(current_position=node.position)
            node.protocol_encapsulator.handle_telemetry(telemetry)

        self._event_loop.schedule_event(self._event_loop.current_time + self._configuration.update_rate,
                                        self._update_movement,
                                       "Mobility")

    def handle_command(self, command: MobilityCommand, node: Node):
        """
        Performs a mobility command. This method is called by the node's 
        provider to transmit it's mobility command to the mobility handler.

        Args:
            command: Command being issued
            node: Node that issued the command
        """
        if node.id not in self._nodes:
            raise MobilityException("Error handling commands: Cannot handle command from unregistered node")

        if command.command == MobilityCommandType.GOTO_COORDS:
            self._goto((command.param_1, command.param_2, command.param_3), node)
        elif command.command == MobilityCommandType.GOTO_GEO_COORDS:
            raise NotImplementedError()
        elif command.command == MobilityCommandType.SET_SPEED:
            self._speeds[node.id] = command.param_1

    def _goto(self, position: Position, node: Node):
        self._targets[node.id] = position

    def _stop(self, node: Node):
        del self._targets[node.id]
