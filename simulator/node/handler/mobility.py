import math
from typing import Dict

from simulator.event import EventLoop
from simulator.messages.mobility import MobilityCommand, MobilityCommandType
from simulator.messages.telemetry import Telemetry
from simulator.node.node import Node
from simulator.position import Position
from simulator.node.handler.interface import INodeHandler


class MobilityException(Exception):
    pass


class MobilityConfiguration:
    def __init__(self,
                 update_rate: float = 0.01,
                 default_speed: float = 10,
                 x_range: Tuple[float, float] = (-50, 50),
                 y_range: Tuple[float, float] = (-50, 50),
                 z_range: Tuple[float, float] = (0, 50),
                 visualization: bool = False,
                 visualization_update_rate: float = 0.1):
        self.update_rate = update_rate
        self.default_speed = default_speed


class MobilityHandler(INodeHandler):
    @staticmethod
    def get_label() -> str:
        return "mobility"

    event_loop: EventLoop

    _nodes: Dict[int, Node]
    _targets: Dict[int, Position]
    _speeds: Dict[int, float]

    def __init__(self, configuration: MobilityConfiguration = MobilityConfiguration()):
        self._configuration = configuration
        self._nodes = {}
        self._targets = {}
        self._speeds = {}
        self._injected = False

    def inject(self, event_loop: EventLoop):
        self._injected = True
        self.event_loop = event_loop

        event_loop.schedule_event(event_loop.current_time + self.settings.update_rate,
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

        self.event_loop.schedule_event(self.event_loop.current_time + self._configuration.update_rate,
                                       self._update_movement,
                                       "Mobility")

    def handle_command(self, command: MobilityCommand, node: Node):
        """
        Performs a mobility command
        :param command: Command being issued
        :param node: Node that issued the command
        """
        if node.id not in self._nodes:
            raise MobilityException("Error handling commands: Cannot handle command from unregistered node")

        if command.command == MobilityCommandType.SET_MODE:
            self._stop(node)
        elif command.command == MobilityCommandType.GOTO_COORDS:
            self._goto((command.param_1, command.param_2, command.param_3), node)
        elif command.command == MobilityCommandType.GOTO_WAYPOINT:
            raise NotImplementedError()
        elif command.command == MobilityCommandType.REVERSE:
            raise NotImplementedError()
        elif command.command == MobilityCommandType.SET_SPEED:
            self._speeds[node.id] = command.param_1

    def _goto(self, position: Position, node: Node):
        self._targets[node.id] = position

    def _stop(self, node: Node):
        del self._targets[node.id]
