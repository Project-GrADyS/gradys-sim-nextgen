import asyncio
import csv
import logging
import os
import random
import statistics
import time
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Type, Optional, Dict, Tuple, Union

from gradysim.encapsulator.python import PythonEncapsulator
from gradysim.protocol.interface import IProtocol
from gradysim.protocol.position import Position
from gradysim.simulator.event import EventLoop
from gradysim.simulator.handler.interface import INodeHandler, IAsyncNodeHandler
from gradysim.simulator.log import setup_simulation_formatter, label_node, format_table
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

    execution_logging: bool = True
    """
    Setting this flag to true will enable logging of the simulation execution. Even if disabled logging will still
    happen at the end of the simulation. Disabling this can improve performance.
    """

    profile: bool = False
    """
    Setting this flag to true will enable profiling of the simulation. This will output to the logs profiling 
    information about the simulation execution. This can be useful to identify bottlenecks in the simulation.
    """

    timing_report: bool = False
    """
    Setting this flag to true writes a CSV with real-time timing information for every iteration to
    timing_report.csv in the current working directory at the end of the simulation, and logs a summary.
    Columns are iteration, simulation_time, real_time, time_until_next_event and time_drift, all in seconds.
    real_time is the wall-clock time since the simulation started (after initialization) when the event was
    executed, time_until_next_event is the wall-clock time the simulation had to wait before the event
    (negative when already late) and time_drift is how far behind the wall clock the event was executed. Only meaningful in
    real-time mode.
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
        self._loop = asyncio.new_event_loop()
        self._nodes: Dict[int, Node] = {}
        self._handlers: Dict[str, INodeHandler] = handlers

        for handler in self._handlers.values():
            handler.inject(self._event_loop)
            if isinstance(handler, IAsyncNodeHandler):
                handler.inject_async(self._loop, float(configuration.real_time))

        self._configuration = configuration

        if self._configuration.real_time < 0:
            raise ValueError("Real time must be greater than 0")

        self._iteration = 0
        self._current_timestamp = 0

        self._formatter = setup_simulation_formatter(configuration.debug, configuration.log_file)
        self._logger = logging.getLogger()

        self._initialized = False
        self._finalized = False

        self._profiling_context_total_count = {}
        self._profiling_context_total_time = {}

        self._timing_samples = []



    def create_node(self, position: Position, protocol: Type[IProtocol], identifier: int) -> Node:
        """
        Creates a new simulation node, encapsulating it. You shouldn't call this method directly, prefer to use the
        [SimulationBuilder][gradysim.simulator.simulation.SimulationBuilder] API.

        Args:
            position: Position where the node should be placed
            protocol: Type of protocol this node will run
            identifier: Identifier of the node

        Returns:
            The encapsulated node
        """
        new_node = Node()
        new_node.id = identifier
        new_node.position = position

        encapsulator = PythonEncapsulator(new_node, **self._handlers)
        encapsulator.encapsulate(protocol)

        new_node.protocol_encapsulator = encapsulator

        for handler in self._handlers.values():
            handler.register_node(new_node)

        self._nodes[new_node.id] = new_node
        return new_node

    def get_node(self, identifier: int) -> Node:
        """
        Gets a node by its identifier

        Args:
            identifier: Identifier of the node

        Returns:
            The encapsulated node
        """
        return self._nodes[identifier]

    def scope_event(self, iteration: int, timestamp: float, context: str):
        """
        Call this method to update the formatter's annotation with current information. This module is called by
        the [Simulator][gradysim.simulator.simulation.Simulator].

        Args:
            iteration: Current iteration the simulation is at
            timestamp: Simulation timestamp in seconds
            context: Context of what's being currently executed in the simulation

        Returns:

        """
        if not self._configuration.execution_logging:
            return

        self._formatter.prefix = f"[it={iteration} time={timedelta(seconds=timestamp)} | {context}] "

    def _initialize_simulation(self) -> None:
        self._initialized = True

        self._old_logger_level = self._logger.level
        if not self._configuration.execution_logging:
            self._logger.setLevel(logging.WARNING)

        for handler in self._handlers.values():
            handler.initialize()

        for node in self._nodes.values():
            self.scope_event(0, 0, f"{label_node(node)} Initialization")
            node.protocol_encapsulator.initialize()

    def _finalize_simulation(self, raise_errors: bool = True) -> None:
        """
        Finalizes protocols and handlers. Each step is isolated so that one failure does not prevent the
        others from cleaning up. If raise_errors is True the first error found is re-raised at the end,
        any other error is logged.
        """
        if self._finalized:
            return
        self._finalized = True

        first_error = None
        try:
            for node in self._nodes.values():
                self.scope_event(self._iteration, 0, f"{label_node(node)} Finalization")
                try:
                    node.protocol_encapsulator.finish()
                except Exception as e:
                    if raise_errors and first_error is None:
                        first_error = e
                    else:
                        self._logger.error(f"Error finalizing {label_node(node)}: {e}", exc_info=e)

            for label, handler in self._handlers.items():
                try:
                    handler.finalize()
                except Exception as e:
                    if raise_errors and first_error is None:
                        first_error = e
                    else:
                        self._logger.error(f"Error finalizing handler '{label}': {e}", exc_info=e)
        finally:
            if not self._loop.is_closed():
                self._loop.run_until_complete(self._loop.shutdown_asyncgens())
                self._loop.close()

        self._formatter.clear_iteration()

        if self._configuration.profile:
            self._logger.info("[--------- Profiling information ---------]")
            contexts = list(self._profiling_context_total_count.keys())
            contexts.sort(key=lambda x: self._profiling_context_total_time[x],
                          reverse=True)
            for context in contexts:
                self._logger.warning(f"Context: {context}\t\t"
                                     f"Total count: {self._profiling_context_total_count[context]}\t\t"
                                     f"Total time: {self._profiling_context_total_time[context]}\t\t"
                                     f"Average time: {self._profiling_context_total_time[context] / self._profiling_context_total_count[context]}")

        if not self._configuration.execution_logging:
            self._logger.setLevel(self._old_logger_level)

        if raise_errors and first_error is not None:
            raise first_error

    def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        try:
            self._initialize_simulation()
        except Exception:
            self._close_async_loop()
            raise

    def step_simulation(self) -> bool:
        """
        Performs a single step in the simulation. This method is useful if you want to run the simulation in a
        non-blocking way. This method will run a single event from the event loop and then return, updating
        the internal simulation state.

        Returns:
            False if the simulation is done, True otherwise
        """
        self._ensure_initialized()

        if self.is_simulation_done():
            self._finalize_simulation()
            return False


        event = self._event_loop.pop_event()
        self.scope_event(self._iteration, event.timestamp, event.context)

        if self._configuration.profile:
            start_time = time.time()
        
        simulation_exception = None

        try:
            event.callback()
        except Exception as e:
            simulation_exception = e
        
        if self._configuration.profile:
            self._profiling_context_total_count[event.context] = (
                    self._profiling_context_total_count.get(event.context, 0) + 1)
            self._profiling_context_total_time[event.context] = (
                    self._profiling_context_total_time.get(event.context, 0) + time.time() - start_time)

        for handler in self._handlers.values():
            handler.after_simulation_step(self._iteration, event.timestamp)

        self._iteration += 1
        self._current_timestamp = event.timestamp

        is_done = self.is_simulation_done()

        if simulation_exception is not None:
            self._logger.error(f"Error while processing event '{event.context}': {simulation_exception}", exc_info=simulation_exception)
            self._logger.error("Finalizing simulation due to error...")
            is_done = True

        if is_done:
            self._finalize_simulation()

        return not is_done

    def start_simulation(self) -> None:
        """
        Call this method to start the simulation. It is a blocking call and runs until either no event is left in the
        event loop or a termination condition is met. If not termination condition is set and events are generated
        infinitely this simulation will run forever.
        """
        start_time = None
        try:
            # Initialization happens before the wall clock reference is taken so that slow handler
            # initializations (e.g. ArdupilotMobilityHandler) do not make every event start late
            self._ensure_initialized()
            self._formatter.clear_iteration()
            self._logger.info("[--------- Simulation started ---------]")
            start_time = time.time()

            real_time = self._configuration.real_time and not _FORCE_FAST_EXECUTION
            speed = float(self._configuration.real_time) or 1

            is_running = True
            while is_running:
                next_event = self._event_loop.peek_event()

                if next_event is not None and real_time:
                    scheduled_time = next_event.timestamp / speed
                    time_until_next_event = scheduled_time - (time.time() - start_time)
                    self._logger.debug(f"Time until next event: {time_until_next_event}")
                    self._logger.debug(f"Next event: {next_event.context} at {timedelta(seconds=next_event.timestamp)}")
                    self._logger.debug(f"Current timestamp: {timedelta(seconds=self._current_timestamp)}")
                    if time_until_next_event > 0:
                        self._logger.debug(f"Sleeping for {timedelta(seconds=time_until_next_event)} until next event")
                        # Asynchronous sleep is used here because some asynchronous coroutines might be running in the background, we can use this sleep
                        # time to advance them.
                        # Example: ArdupilotMobilityHandler uses asynchronous coroutines to read telemetry data from the Ardupilot SITL.
                        self._loop.run_until_complete(asyncio.sleep(time_until_next_event))

                    elapsed = time.time() - start_time
                    time_drift = elapsed - scheduled_time
                    self._logger.debug(f"Time drift: {time_drift}")
                    if self._configuration.timing_report:
                        self._timing_samples.append(
                            (self._iteration, next_event.timestamp, elapsed, time_until_next_event, time_drift))

                is_running = self.step_simulation()
        except KeyboardInterrupt:
            self._logger.warning("Simulation interrupted, finalizing...")
            self._finalize_simulation(raise_errors=False)
            raise
        finally:
            self._report_timing()

        self._logger.info("[--------- Simulation finished ---------]")
        total_time = time.time() - start_time

        self._logger.info(f"Real time elapsed: {timedelta(seconds=total_time)}\t"
                          f"Total iterations: {self._iteration}\t"
                          f"Simulation time: {timedelta(seconds=self._current_timestamp)}")

    def _report_timing(self) -> None:
        """
        Writes the timing samples collected during a real-time simulation to a CSV file and logs a summary
        """
        if not self._configuration.timing_report or not self._timing_samples:
            return

        csv_path = os.path.abspath("timing_report.csv")
        try:
            with open(csv_path, "w", newline="") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["iteration", "simulation_time", "real_time", "time_until_next_event", "time_drift"])
                writer.writerows(self._timing_samples)
            saved_line = f"Report saved to {csv_path}"
        except Exception as e:
            saved_line = f"Could not save report to {csv_path}: {e}"

        rows = []
        for name, column in (("time_until_next_event", 3), ("time_drift", 4)):
            values = [sample[column] for sample in self._timing_samples]
            rows.append([name] + [f"{value:.4f}" for value in (values[-1], statistics.fmean(values), max(values))])
        table = format_table(["Metric", "Last (s)", "Mean (s)", "Max (s)"], rows)
        _, final_simulation_time, final_real_time, _, _ = self._timing_samples[-1]
        # Simulation seconds executed per wall-clock second, 1.0 means the simulation kept up with real time
        real_time_factor = f"{final_simulation_time / final_real_time:.4f}" if final_real_time > 0 else "n/a"
        self._logger.info(f"Timing report\n{table}\n"
                          f"  Final simulation time: {final_simulation_time:.4f} s\n"
                          f"  Final wall-clock time: {final_real_time:.4f} s\n"
                          f"  Configured real_time:  {float(self._configuration.real_time):g}\n"
                          f"  Real time factor:      {real_time_factor}\n"
                          f"{saved_line}")

    def is_simulation_done(self) -> bool:
        """
        Checks if the simulation is done. The simulation is done if any of the termination conditions are met or
        if there are no mode events

        Returns:
            True if the simulation is done, False otherwise
        """
        if len(self._event_loop) == 0:
            return True

        if self._configuration.duration is not None:
            current_time = self._event_loop.current_time

            if current_time > self._configuration.duration:
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

    def add_node(self, protocol: Type[IProtocol], position: Position) -> int:
        """
        Adds a new node to the simulation

        Args:
            protocol: Type of protocol this node will run
            position: Position of the node inside the simulation

        Returns:
            The id of the node created
        """
        self._nodes_to_add.append((position, protocol))
        return len(self._nodes_to_add) - 1

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
        for index, node_to_add in enumerate(self._nodes_to_add):
            simulator.create_node(node_to_add[0], node_to_add[1], index)

        return simulator