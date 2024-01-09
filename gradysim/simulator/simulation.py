import logging
import random
import time
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Type, Optional, Dict, Tuple, Union

from gradysim.encapsulator.python import PythonEncapsulator
from gradysim.protocol.interface import IProtocol
from gradysim.protocol.position import Position
from gradysim.simulator.event import EventLoop
from gradysim.simulator.handler.interface import INodeHandler
from gradysim.simulator.log import setup_simulation_formatter, label_node
from gradysim.simulator.node import Node

_FORCE_FAST_EXECUTION = False


class _ForceFastExecution:
    """
    This class is only used for integration testing purposes, you shouldn't need to use it ever. It is used to force
    the simulation to run as fast as possible. This is useful for integration testing because it makes the tests run
    faster. Use it as a context with the `with` keyword
    """

    def __enter__(self):
        global _FORCE_FAST_EXECUTION
        _FORCE_FAST_EXECUTION = True

    def __exit__(self, _exc_type, _exc_val, _exc_tb):
        global _FORCE_FAST_EXECUTION
        _FORCE_FAST_EXECUTION = False


@dataclass
class SimulationConfiguration:
    """
    Simulation-level configurations. These will change how the simulation will be run.
    """
    duration: Optional[float] = None
    """
    Maximum duration of the simulation in seconds. The simulation will end when no more events scheduled before 
    `duration` are left. If `None`, no limit is set.
    """

    max_iterations: Optional[int] = None
    """
    Maximum number of simulation iterations. An iteration is counted every time an event is popped from the event-loop.
    If `None`, no limit is set.
    """

    real_time: Union[bool, float] = False
    """
    Setting this to true will put the simulation in real-time mode. This means that the simulation will run synchronized
    with real-world time. One simulation second will approximately equal to one real-world second. If set to a float
    will run at that many times real-time. For example, setting this to 2 will make the simulation run twice as fast as
    real-time. The float value must be greater than 0.
    """

    debug: bool = False
    """
    Setting this flag to true will enable additional logging. Helpful if you are having issues with the simulation.
    """

    log_file: Optional[Path] = None
    """
    Simulation logs will be saved in this path.
    """


class Simulator:
    """
    Executes the python simulation by managing the event loop. This class is responsible for making sure handlers'
    get the event loop instance they need to function, implementing simulation-level configurations like termination
    conditions and configuring logging.

    You shouldn't instantiate this class directly, prefer to build it through
    [SimulationBuilder][gradysim.simulator.simulation.SimulationBuilder].
    """

    def __init__(self, handlers: Dict[str, INodeHandler], configuration: SimulationConfiguration):
        """
        Instantiates the simulation class. This constructor should not be called directly, prefer to use the
        [SimulationBuilder][gradysim.simulator.simulation.SimulationBuilder] API to get a simulator instance.

        Args:
            handlers: Dictionary of handlers indexed by their labels
            configuration: Simulation configuration
        """
        self._event_loop = EventLoop()
        self._nodes: Dict[int, Node] = {}
        self._handlers: Dict[str, INodeHandler] = handlers

        for handler in self._handlers.values():
            handler.inject(self._event_loop)

        self._free_id = 0
        self._configuration = configuration

        if self._configuration.real_time < 0:
            raise ValueError("Real time must be greater than 0")

        self._iteration = 0

        self._formatter = setup_simulation_formatter(configuration.debug, configuration.log_file)
        self._logger = logging.getLogger()

    def create_node(self, position: Position, protocol: Type[IProtocol]) -> Node:
        """
        Creates a new simulation node, encapsulating it. You shouldn't call this method directly, prefer to use the
        [SimulationBuilder][gradysim.simulator.simulation.SimulationBuilder] API.

        Args:
            position: Position where the node should be placed
            protocol: Type of protocol this node will run

        Returns:
            The encapsulated node
        """
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

    def start_simulation(self) -> None:
        """
        Call this method to start the simulation. It is a blocking call and runs until either no event is left in the
        event loop or a termination condition is met. If not termination condition is set and events are generated
        infinitely this simulation will run forever.
        """
        self._logger.info("[--------- Simulation started ---------]")
        start_time = time.time()

        for handler in self._handlers.values():
            handler.initialize()

        for node in self._nodes.values():
            self._formatter.scope_event(0, 0, f"{label_node(node)} Initialization")
            node.protocol_encapsulator.initialize()

        last_timestamp = 0
        event_duration = 0
        while not self._is_simulation_done():
            event = self._event_loop.pop_event()

            if self._configuration.real_time and not _FORCE_FAST_EXECUTION:
                sleep_duration = (event.timestamp - (last_timestamp + event_duration)) / self._configuration.real_time
                if sleep_duration > 0:
                    time.sleep(sleep_duration)

            self._formatter.scope_event(self._iteration, event.timestamp, event.context)

            event_start = time.time()
            event.callback()
            event_duration = time.time() - event_start

            for handler in self._handlers.values():
                handler.after_simulation_step(self._iteration, event.timestamp)

            self._iteration += 1
            last_timestamp = event.timestamp

        self._formatter.clear_iteration()
        self._logger.info("[--------- Simulation finished ---------]")
        total_time = time.time() - start_time

        for node in self._nodes.values():
            self._formatter.scope_event(0, 0, f"{label_node(node)} Finalization")
            node.protocol_encapsulator.finish()

        for handler in self._handlers.values():
            handler.finalize()

        self._formatter.clear_iteration()

        self._logger.info(f"Real time elapsed: {timedelta(seconds=total_time)}\t"
                          f"Total iterations: {self._iteration}\t"
                          f"Simulation time: {timedelta(seconds=last_timestamp)}")

    def _is_simulation_done(self):
        if len(self._event_loop) == 0:
            return True

        if self._configuration.duration is not None:
            current_time = self._event_loop.current_time
            next_event = self._event_loop.peek_event()

            if current_time >= self._configuration.duration:
                if next_event is None or next_event.timestamp > self._configuration.duration:
                    return True

        if self._configuration.max_iterations is not None and self._iteration >= self._configuration.max_iterations:
            return True

        return False


class PositionScheme:
    """
    Collection of helpers for positioning your nodes within the simulation.
    """

    @staticmethod
    def random(x_range: Tuple[float, float] = (-10, 10),
               y_range: Tuple[float, float] = (-10, 10),
               z_range: Tuple[float, float] = (0, 10)) -> Position:
        """
        Generates a random position
        Args:
            x_range: Range of possible positions in the x axis
            y_range: Range of possible positions in the y axis
            z_range: Range of possible positions in the z axis

        Returns:
            A random position within the specified ranges
        """
        return (
            random.uniform(*x_range),
            random.uniform(*y_range),
            random.uniform(*z_range)
        )


class SimulationBuilder:
    """
    Helper class to build python simulations. Use the `add_handler` and `add_node` methods to build your simulation
    scenario them call `build()` to get a simulation instance. Use this class instead of directly trying to instantiate
    a `Simulator` instance.

    A simulation is build through a fluent interface. This means that you after instantiating this builder class you
    will set up your simulation by calling methods on that instance gradually building up your simulation.

    All methods return the [SimulationBuilder][gradysim.simulator.simulation.SimulationBuilder] instance to help you with method chaining.
    """

    def __init__(self,
                 configuration: SimulationConfiguration = SimulationConfiguration()):
        """
        Initializes the simulation builder

        Args:
            configuration: Configuration used for the simulation. The default values uses all default values from the `SimulationConfiguration` class
        """
        self._configuration = configuration
        self._handlers: Dict[str, INodeHandler] = {}
        self._nodes_to_add: list[Tuple[Position, Type[IProtocol]]] = []

    def add_handler(self, handler: INodeHandler) -> 'SimulationBuilder':
        """
        Adds a new handler to the simulation

        Args:
            handler: A handler instance

        Returns:
            The simulator builder instance. This is useful for method chaining
        """
        self._handlers[handler.get_label()] = handler
        return self

    def add_node(self, protocol: Type[IProtocol], position: Position) -> 'SimulationBuilder':
        """
        Adds a new node to the simulation

        Args:
            protocol: Type of protocol this node will run
            position: Position of the node inside the simulation

        Returns:
            The simulator builder instance. This is useful for method chaining
        """
        self._nodes_to_add.append((position, protocol))
        return self

    def build(self) -> Simulator:
        """
        Builds the simulation. Should only be called after you have already added all nodes and handlers. Nodes
        and handlers added after this call will not affect the instance returned by this method.

        Returns:
            Simulator instance configured using the previously called methods
        """
        simulator = Simulator(
            self._handlers,
            self._configuration
        )
        for node_to_add in self._nodes_to_add:
            simulator.create_node(*node_to_add)

        return simulator
