import logging
import random
import time
from datetime import timedelta
from pathlib import Path
from typing import Type, Optional, Dict, Tuple

from simulator.encapsulator.python import PythonEncapsulator
from simulator.event import EventLoop
from simulator.log import SIMULATION_LOGGER, setup_simulation_formatter
from simulator.node.node import Node
from simulator.position import Position
from simulator.node.handler.communication import CommunicationMedium, CommunicationHandler
from simulator.node.handler.timer import TimerHandler
from simulator.node.handler.interface import INodeHandler
from simulator.protocols.interface import IProtocol


class SimulationConfiguration:
    duration: Optional[float]
    real_time: bool
    debug: bool
    log_file: Optional[Path]

    def __init__(self, duration: Optional[float] = None, real_time=False, debug=False, log_file: Optional[Path] = None):
        self.duration = duration
        self.real_time = real_time
        self.debug = debug
        self.log_file = log_file


class Simulator:
    def __init__(self, handlers: Dict[str, INodeHandler], configuration: SimulationConfiguration):
        self._event_loop = EventLoop()
        self._nodes: Dict[int, Node] = {}
        self._handlers: Dict[str, INodeHandler] = handlers

        for handler in self._handlers.values():
            handler.inject(self._event_loop)

        self._free_id = 0
        self._configuration = configuration

        self._iteration = 0

        self._formatter = setup_simulation_formatter(configuration.debug, configuration.log_file)
        self._logger = logging.getLogger(SIMULATION_LOGGER)

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
        self._logger.info("[--------- Simulation started ---------]")
        start_time = time.time()
        for node in self._nodes.values():
            node.protocol_encapsulator.initialize(1)

        while not self._is_simulation_done():
            event = self._event_loop.pop_event()

            self._formatter.scope_event(self._iteration, event.timestamp, event.handler)

            event.callback()

            self._iteration += 1

        self._formatter.clear_iteration()
        self._logger.info("[--------- Simulation finished ---------]")
        total_time = time.time() - start_time

        try:
            last_timestamp = event.timestamp
        except NameError:
            last_timestamp = 0

        self._logger.info(f"Real time elapsed: {timedelta(seconds=total_time)}\t"
                          f"Total iterations: {self._iteration}\t"
                          f"Simulation time: {timedelta(seconds=last_timestamp)}")

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
    def __init__(self,
                 configuration: SimulationConfiguration,
                 communication_medium: CommunicationMedium = None):
        self._configuration = configuration
        self._handlers: Dict[str, INodeHandler] = {}
        self._nodes_to_add: list[Tuple[Position, Type[IProtocol]]] = []

        self.add_handler(CommunicationHandler(communication_medium or CommunicationMedium()))
        self.add_handler(TimerHandler())

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
