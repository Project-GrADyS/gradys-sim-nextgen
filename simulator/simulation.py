import logging
import random
from typing import Type, Optional, Dict, Tuple

from simulator.encapsulator.python import PythonEncapsulator
from simulator.event import EventLoop
from simulator.node import Node, Position
from simulator.node.interface import INodeHandler
from simulator.protocols.interface import IProtocol


class SimulationConfiguration:
    duration: Optional[float]
    real_time: bool
    debug: bool

    def __init__(self, duration: Optional[float] = None, real_time=False, debug=False):
        self.duration = duration
        self.real_time = real_time

        if debug:
            logging.basicConfig(level=logging.DEBUG)


class Simulator:
    def __init__(self, handlers: Dict[str, INodeHandler], configuration: SimulationConfiguration):
        self._event_loop = EventLoop()
        self._nodes: Dict[int, Node] = {}
        self._handlers: Dict[str, INodeHandler] = handlers

        for handler in self._handlers.values():
            handler.inject(self._event_loop)

        self._free_id = 0
        self._configuration = configuration

    def create_node(self, position: Position, protocol: Type[IProtocol]) -> Node:
        new_node = Node()
        new_node.id = self._free_id
        new_node.position = position

        encapsulator = PythonEncapsulator(new_node, **self._handlers)
        encapsulator.encapsulate(protocol)

        new_node.protocol_encapsulator = encapsulator

        for handler in self._handlers.values():
            handler.register_node(new_node)

        self._free_id += 1
        self._nodes[new_node.id] = new_node
        return new_node

    def start_simulation(self):
        for node in self._nodes.values():
            node.protocol_encapsulator.initialize(1)

        while not self._is_simulation_done():
            event = self._event_loop.pop_event()
            event.callback()

    def _is_simulation_done(self):
        if len(self._event_loop) == 0:
            return True

        if self._event_loop.current_time > self._configuration.duration:
            return True

        return False


class PositionScheme:
    @staticmethod
    def random(x_range: Tuple[float, float] = (-10, 10),
               y_range: Tuple[float, float] = (-10, 10),
               z_range: Tuple[float, float] = (0, 10)) -> Position:
        return (
            random.uniform(*x_range),
            random.uniform(*y_range),
            random.uniform(*z_range)
        )


class SimulationBuilder:
    def __init__(self, configuration: SimulationConfiguration):
        self._configuration = configuration
        self._handlers: Dict[str, INodeHandler] = {}
        self._nodes_to_add: list[Tuple[Position, Type[IProtocol]]] = []

    def add_handler(self, handler: INodeHandler):
        self._handlers[handler.get_label()] = handler

    def add_node(self, protocol: Type[IProtocol], position: Position):
        self._nodes_to_add.append((position, protocol))

    def build(self) -> Simulator:
        simulator = Simulator(
            self._handlers,
            self._configuration
        )
        for node_to_add in self._nodes_to_add:
            simulator.create_node(*node_to_add)

        return simulator
