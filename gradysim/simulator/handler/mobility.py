import math
from dataclasses import dataclass
from typing import Dict, Tuple

from gradysim.protocol.messages.mobility import MobilityCommand, MobilityCommandType
from gradysim.protocol.messages.telemetry import Telemetry
from gradysim.protocol.position import Position, geo_to_cartesian
from gradysim.simulator.event import EventLoop
from gradysim.simulator.handler.interface import INodeHandler
from gradysim.simulator.log import label_node
from gradysim.simulator.node import Node


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

    reference_coordinates: Tuple[float, float, float] = (0, 0, 0)
    """
    These coordinates are used as a reference frame to convert geographical coordinates to cartesian coordinates. They
    will be used as the center of the scene and all geographical coordinates will be converted relative to it.
    """


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

    nodes: Dict[int, Node]
    targets: Dict[int, Position]
    speeds: Dict[int, float]

    def __init__(self, configuration: MobilityConfiguration = MobilityConfiguration()):
        """
        Constructor for the mobility handler

        Args:
            configuration: Configuration for the mobility handler. If not set all default values will be used.
        """
        self._configuration = configuration
        self.nodes = {}
        self.targets = {}
        self.speeds = {}
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

        self.nodes[node.id] = node
        self.speeds[node.id] = self._configuration.default_speed

    def _update_movement(self):
        for node_id in self.nodes.keys():
            node = self.nodes[node_id]

            # If the node has a target update its position
            if node_id in self.targets:
                target = self.targets[node_id]
                current_position = node.position
                speed = self.speeds[node_id]
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

            def make_send_telemetry(node_ref, telemetry_ref):
                return lambda: node_ref.protocol_encapsulator.handle_telemetry(telemetry_ref)

            self._event_loop.schedule_event(
                self._event_loop.current_time,
                make_send_telemetry(node, telemetry),
                label_node(node) + " handle_telemetry"
            )

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
        if node.id not in self.nodes:
            raise MobilityException("Error handling commands: Cannot handle command from unregistered node")

        if command.command_type == MobilityCommandType.GOTO_COORDS:
            self._goto((command.param_1, command.param_2, command.param_3), node)
        elif command.command_type == MobilityCommandType.GOTO_GEO_COORDS:
            relative_coords = geo_to_cartesian(self._configuration.reference_coordinates,
                                               (command.param_1, command.param_2, command.param_3))
            self._goto(relative_coords, node)
        elif command.command_type == MobilityCommandType.SET_SPEED:
            self.speeds[node.id] = command.param_1

    def _goto(self, position: Position, node: Node):
        self.targets[node.id] = position

    def _stop(self, node: Node):
        del self.targets[node.id]
