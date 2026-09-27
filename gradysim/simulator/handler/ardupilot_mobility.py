import os
import sys
import time
import aiohttp
import asyncio
import logging
import csv
import multiprocessing

from asyncio import AbstractEventLoop

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from gradysim.protocol.messages.mobility import MobilityCommand, MobilityCommandType
from gradysim.protocol.messages.telemetry import Telemetry
from gradysim.protocol.position import Position
from gradysim.simulator.event import EventLoop
from gradysim.simulator.handler.interface import IAsyncNodeHandler
from gradysim.simulator.log import format_table
from gradysim.simulator.node import Node

from uav_api.run_api import spawn_with_args, run_with_args

REQUEST_TIMEOUT = 10
COMMAND_RETRY_TIME = 5
TELEMETRY_TIMEOUT = 5
REPORT_TIMEOUT = 5
PROCESS_EXIT_TIMEOUT = 10
LOG_PREFIX = "[ArdupilotMobility]"

def _run_uav_api_quietly(raw_args):
    """
    Entry point for a UAV API process whose console output is discarded. UAV API still writes
    its own log file. Must live at module level so it can be pickled by multiprocessing.
    """
    devnull = os.open(os.devnull, os.O_WRONLY)
    # Redirecting the file descriptors also silences subprocesses spawned by UAV API (SITL)
    os.dup2(devnull, 1)
    os.dup2(devnull, 2)
    sys.stdout = sys.stderr = open(os.devnull, "w")
    run_with_args(raw_args)

def _ned(position: Position) -> dict:
    """Translates a position in the simulation XYZ frame to the NED frame used by UAV API"""
    return {"x": position[0], "y": position[1], "z": -position[2]}

class ArdupilotMobilityException(Exception):
    pass

class Drone:
    """
    Represents the Ardupilot version of the Node. Each Node has an equivalent Drone instance, which owns
    the UAV API process (in simulated mode), an HTTP session to it and a co-routine that consumes a queue
    of requests to UAV API, implementing Mobility Commands and Telemetry updates.
    """

    def __init__(self, node_id, initial_position, logger, api_port):
        self._node_id = node_id
        self._logger = logger
        self._api_port = api_port + node_id
        self._session: Optional[aiohttp.ClientSession] = None
        self._consumer_task = None
        self._api_process = None
        self._log_path = None

        self.queue = asyncio.Queue()
        """Asynchronous functions without arguments, awaited in order by the request consumer"""
        self.position = initial_position
        self.telemetry_requested = False

    async def request(self, method, path, timeout: Optional[float] = REQUEST_TIMEOUT, retry_for: float = 0,
                      **kwargs) -> dict:
        """
        Performs an HTTP request to this drone's UAV API and returns its JSON response. Transient failures
        (connection errors, timeouts and 5xx responses) are retried with exponential backoff until retry_for
        seconds have passed, this is also how requests wait for a UAV API that is still starting. Other
        failures raise immediately.

        Args:
            method: HTTP method
            path: path of the UAV API endpoint
            timeout: timeout in seconds of each attempt, None disables it
            retry_for: time in seconds during which transient failures are retried
            kwargs: forwarded to aiohttp (params, json)
        """
        deadline = time.monotonic() + retry_for
        backoff = 0.25
        while True:
            try:
                async with self._session.request(method, path, timeout=aiohttp.ClientTimeout(total=timeout),
                                                 **kwargs) as response:
                    return await response.json()
            except (aiohttp.ClientConnectionError, aiohttp.ClientResponseError, asyncio.TimeoutError) as e:
                transient = not isinstance(e, aiohttp.ClientResponseError) or e.status >= 500
                if not transient or time.monotonic() + backoff > deadline:
                    raise
                # Retrying is pointless if the UAV API process is gone
                if self._api_process is not None and not self._api_process.is_alive():
                    raise ArdupilotMobilityException(
                        f"UAV API for drone {self._node_id} exited (exit code {self._api_process.exitcode}). "
                        f"See {self._log_path}") from e
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 2)

    async def update_telemetry(self):
        """
        Updates the drone position from UAV API telemetry and marks the telemetry request as fulfilled.
        """
        # Not retried, the next telemetry event requests a new update anyway
        position = (await self.request("GET", "/telemetry/ned", timeout=TELEMETRY_TIMEOUT))["info"]["position"]
        self.position = (position["x"], position["y"], -position["z"]) # translating NED frame to XYZ frame
        self.telemetry_requested = False

    async def _consume(self):
        """
        Awaits the requests in the queue in order. A failed request is logged and does not stop the consumer.
        """
        while True:
            request = await self.queue.get()
            try:
                await request()
            except Exception as e:
                self._logger.debug(f"[DRONE-{self._node_id}] Error handling request: {e}")

    def spawn(self, configuration: "ArdupilotMobilityConfiguration"):
        """
        Starts a simulated UAV API instance (and its SITL) for this drone without waiting for it to be ready,
        requests are retried while it starts. The process output is discarded unless uav_api_log_console is
        set, UAV API still writes its log file.
        """
        sysid = self._node_id + 10
        raw_args = [
            '--simulated',
            '--headless',
            '--sysid', str(sysid),
            '--port', str(self._api_port),
            '--uav_connection', f'127.0.0.1:17{171 + self._node_id}',
            '--speedup', str(configuration.simulation_startup_speedup),
        ]
        optional_args = {
            "--gs_connection": configuration.ground_station_ip,
            "--ardupilot_path": configuration.ardupilot_path,
            "--log_path": configuration.uav_api_log_path,
        }
        for flag, value in optional_args.items():
            if value is not None:
                raw_args += [flag, value]
        # Default log location used by UAV API
        self._log_path = configuration.uav_api_log_path or \
            os.path.expanduser(f"~/.uav_api/logs/uav_logs/uav_{sysid}.log")

        if configuration.uav_api_log_console:
            self._api_process = spawn_with_args(raw_args)
        else:
            self._api_process = multiprocessing.Process(target=_run_uav_api_quietly, args=(raw_args,))
            self._api_process.start()

    async def start(self, sim_speedup: Optional[float], startup_timeout: float):
        """
        Opens the HTTP session and drives the vehicle to the simulation starting point, then starts the
        request consumer. Simulated vehicles are spawned with SITL running at simulation_startup_speedup, once
        the starting point is reached SITL is set to sim_speedup. None skips it (real vehicles).

        The first request is retried for startup_timeout seconds while UAV API is starting, every step has
        startup_timeout seconds to complete.
        """
        self._session = aiohttp.ClientSession(base_url=f"http://localhost:{self._api_port}", raise_for_status=True)

        steps = [
            ("GET", "/command/arm", {"retry_for": startup_timeout}),
            ("GET", "/command/takeoff", {"params": {"alt": 10}}),
            ("POST", "/movement/go_to_ned_wait", {"json": _ned(self.position)}),
        ]
        if sim_speedup is not None:
            steps.append(("GET", "/command/set_sim_speedup", {"params": {"sim_factor": sim_speedup}}))

        for method, path, kwargs in steps:
            self._logger.debug(f"[DRONE-{self._node_id}] {method} {path} {kwargs}")
            await self.request(method, path, timeout=startup_timeout, **kwargs)

        self._consumer_task = asyncio.create_task(self._consume())
        await self.update_telemetry()

    async def battery(self) -> Optional[float]:
        """
        Returns the remaining vehicle battery in percentage, or None if it is unavailable
        """
        try:
            return (await self.request("GET", "/telemetry/battery_info"))["info"]["battery_remaining"]
        except Exception as e:
            self._logger.debug(f"[DRONE-{self._node_id}] Error fetching battery level: {e}")
            return None

    def terminate_process(self, timeout=PROCESS_EXIT_TIMEOUT) -> bool:
        """
        Terminates the UAV API process and waits for it to exit. If it does not exit in time it is killed.

        Returns:
            True if the process exited cleanly (or was not running), False otherwise
        """
        if self._api_process is None:
            return True

        process = self._api_process
        self._api_process = None
        process.terminate()
        process.join(timeout)
        if process.is_alive():
            process.kill()
            process.join()
            self._logger.warning(f"{LOG_PREFIX} UAV API for drone {self._node_id} did not exit in {timeout}s and "
                                 f"was killed. SITL may still be running")
            return False
        return True

    async def shutdown(self) -> bool:
        """
        Cancels the request consumer, closes the HTTP session and terminates the UAV API process.

        Returns:
            True if every step succeeded, False otherwise
        """
        if self._consumer_task is not None:
            self._consumer_task.cancel()
            await asyncio.gather(self._consumer_task, return_exceptions=True)

        clean = True
        if self._session is not None:
            try:
                await self._session.close()
            except Exception as e:
                clean = False
                self._logger.warning(f"[DRONE-{self._node_id}] Error closing HTTP session: {e}")
            self._session = None

        # Runs in a thread so that drones wait for their processes in parallel
        return await asyncio.to_thread(self.terminate_process) and clean

@dataclass
class ArdupilotMobilityConfiguration:
    """
    Configuration class for the Ardupilot mobility handler
    """

    update_rate: float = 0.1
    """Interval in simulation seconds between Ardupilot telemetry updates"""

    default_speed: float = 10
    """Default starting airspeed of a node in m/s"""

    reference_coordinates: Tuple[float, float, float] = (0, 0, 0)
    """
    These coordinates are used as a reference frame to convert geographical coordinates to cartesian coordinates. They
    will be used as the center of the scene and all geographical coordinates will be converted relative to it.
    """

    generate_report: bool = True
    """Whether to output a report in the end of the simulation or not"""
    
    simulate_drones: bool = True
    """Wheter to use SITL or connect to real vehicle"""

    ground_station_ip: str = None
    """If provided and simulate_drones is True, this ip is used in UAV API to connect a GroundStation software to the simulated vehicle"""

    starting_api_port: int = 8000
    """
    The port in which UAV API of Node 0 will run. Following nodes use the ports in sequence by
    the formula port_of_node_{node_id} = starting_api_port + {node_id}
    """

    ardupilot_path: str = None
    """Path for cloned ardupilot repository. Used for SITL initialization when in simulated mode"""

    uav_api_log_path: str = None
    """Path in which UAV API will save log files. Used in simulated mode."""

    uav_api_startup_timeout: float = 120
    """
    Maximum time in seconds a drone's UAV API has to start accepting requests, and each setup step (arm,
    takeoff, reaching the initial position) has to complete.
    """

    uav_api_log_console: bool = False
    """
    Whether to show UAV API and SITL output in the console. When False their output is discarded,
    UAV API still writes its log file (see uav_api_log_path). Used in simulated mode.
    """

    simulation_startup_speedup: int = 10
    """
    SITL speedup used while drones are set up (UAV API spawn, takeoff and reaching the initial position),
    passed to UAV API when it is spawned. Once all drones are ready, SITL is set to match the simulation's
    real_time factor. Only used in simulated mode. Values above ~10 may introduce MAVLink timing artifacts.
    """
class ArdupilotMobilityHandler(IAsyncNodeHandler):
    """
    Introduces mobility into the simulatuon by communicating with a SITL-based simulation of the Node. Works by
    sending requests to UAV API library which connects to the Ardupilot software. It implements telemetry by
    constantly making requests to 'telemetry/ned' at a fixed rate and translating mobility commands into HTTP
    requests to UAV API
    """
    @staticmethod
    def get_label() -> str:
        return "mobility"

    _event_loop: EventLoop
    _configuration: ArdupilotMobilityConfiguration
    _logger: logging.Logger
    _report: Dict[int, dict]
    _injected: bool

    nodes: Dict[int, Node]
    drones: Dict[int, Drone]
    def __init__(self, configuration: ArdupilotMobilityConfiguration = ArdupilotMobilityConfiguration()):
        """
        Constructor for the Ardupilot mobility handler

        Args:
            configuration: Configuration for the Ardupilot mobility handle. This includes parameters used in
            UAV API initialization If not set all default values will be used.
        """
        self._configuration = configuration
        self.nodes = {}
        self.drones = {}
        self._injected = False
        self._logger = logging.getLogger()
        self._report = {}
        self._loop = None
        self._real_time = 1.0
        self._shut_down = False

    def inject(self, event_loop: EventLoop):
        self._injected = True
        self._event_loop = event_loop

    def inject_async(self, asyncio_loop: AbstractEventLoop, real_time: float):
        self._loop = asyncio_loop
        self._real_time = real_time

    def register_node(self, node: Node):
        """
        Instantiates Drone object equivalent to the Node provided. Starts the UAV API
        process associated with this instance.

        Args:
            node: the Node instance that will be registered in the handler
        """
        if not self._injected:
            raise ArdupilotMobilityException("Error registering node: cannot register nodes while Ardupilot "
                                             "mobility handler is uninitialized.")

        drone = Drone(node.id, node.position, self._logger, self._configuration.starting_api_port)
        self.drones[node.id] = drone

        if self._configuration.simulate_drones:
            self._logger.info(f"{LOG_PREFIX} Starting simulated drone {node.id} (UAV API on port {drone._api_port})...")
            try:
                drone.spawn(self._configuration)
            except Exception as e:
                # The simulator is not finalized during build, so processes already spawned must be stopped here
                for spawned_drone in self.drones.values():
                    spawned_drone.terminate_process()
                raise ArdupilotMobilityException(f"Error starting drone {node.id}: {e}") from e
        self.nodes[node.id] = node

    def initialize(self):
        """
        Drives every drone to its starting point concurrently, initializes the report and starts the
        recurrent telemetry events. If any drone fails, every drone is shut down.
        """
        if self._loop is None:
            raise ArdupilotMobilityException("No async loop provided. inject_async was never called")

        if self._real_time <= 0:
            self._logger.warning(f"{LOG_PREFIX} The simulation is not running in real-time mode. SITL runs on the "
                                 f"wall clock, so the simulation will diverge from it. Enable real_time in "
                                 f"SimulationConfiguration")
        if not self._configuration.simulate_drones and self._real_time not in (0, 1):
            self._logger.warning(f"{LOG_PREFIX} Real vehicles cannot be sped up, the simulation running at "
                                 f"{self._real_time:g}x real time will diverge from them")

        # Real vehicles cannot be sped up
        sim_speedup = (self._real_time if self._real_time > 0 else 1.0) if self._configuration.simulate_drones else None
        startup_timeout = self._configuration.uav_api_startup_timeout

        self._logger.info(f"{LOG_PREFIX} Waiting for {len(self.drones)} drones to reach their initial positions...")
        try:
            self._run_all(drone.start(sim_speedup, startup_timeout) for drone in self.drones.values())
        except Exception as e:
            self._shutdown()
            raise ArdupilotMobilityException(f"Error initializing drones: {e}") from e

        speedup_info = f", SITL speedup {sim_speedup:g}x" if sim_speedup not in (None, 1) else ""
        for node_id, drone in self.drones.items():
            position = tuple(round(coordinate, 2) for coordinate in drone.position)
            self._logger.info(f"{LOG_PREFIX} Drone {node_id} ready (UAV API on port {drone._api_port}, "
                              f"at initial position {position}{speedup_info})")
        self._logger.info(f"{LOG_PREFIX} All {len(self.drones)} drones initialized")

        if self._configuration.generate_report:
            batteries = self._run_all(drone.battery() for drone in self.drones.values())
            for node_id, battery in zip(self.drones, batteries):
                if battery is None:
                    self._logger.warning(f"{LOG_PREFIX} Could not read initial battery level of drone {node_id}, "
                                         f"battery consumption will be unavailable in the report")
                self._report[node_id] = {"initial_battery": battery, "telemetry_requests": 0, "telemetry_drops": 0}

        for node_id in self.nodes:
            self._event_loop.schedule_event(self._event_loop.current_time,
                                            lambda node_id=node_id: self._send_telemetry(node_id), "ArdupilotMobility")

    def _send_telemetry(self, node_id):
        """
        Recurrent telemetry event, fired at update_rate. If the last telemetry request was fulfilled, the updated
        position is delivered to the node and a new update is requested. If not, this update is dropped.
        """
        node = self.nodes[node_id]
        drone = self.drones[node_id]

        if self._configuration.generate_report:
            self._report[node_id]["telemetry_requests"] += 1
        if drone.telemetry_requested:
            if self._configuration.generate_report:
                self._report[node_id]["telemetry_drops"] += 1
            self._logger.debug(f"Telemetry already requested for node {node_id}, skipping.")
        else:
            node.position = drone.position
            node.protocol_encapsulator.handle_telemetry(Telemetry(current_position=node.position))
            drone.telemetry_requested = True
            drone.queue.put_nowait(drone.update_telemetry)

        self._event_loop.schedule_event(self._event_loop.current_time + self._configuration.update_rate,
                                        lambda: self._send_telemetry(node_id), "ArdupilotMobility")

    def handle_command(self, command: MobilityCommand, node: Node):
        """
        Performs a mobility command in the SITL-based simulation. This method is called
        by the node's provider to transmit it's mobility command to the ardupilot mobility
        handler and then to the node's UAV API.

        Args:
            command: Command being issued
            node: Node that issued the command
        """
        if node.id not in self.drones:
            raise ArdupilotMobilityException("Error handling commands: Cannot handle command from unregistered node")
        self._logger.debug(f"Handling command: {command.command_type}, {command.param_1}, {command.param_2}, {command.param_3}")

        match command.command_type:
            case MobilityCommandType.GOTO_COORDS:
                request = ("POST", "/movement/go_to_ned",
                           {"json": _ned((command.param_1, command.param_2, command.param_3))})
            case MobilityCommandType.GOTO_GEO_COORDS:
                request = ("POST", "/movement/go_to_gps",
                           {"json": {"lat": command.param_1, "long": command.param_2, "alt": command.param_3}})
            case MobilityCommandType.SET_SPEED:
                request = ("GET", "/command/set_air_speed", {"params": {"new_v": command.param_1}})
            case MobilityCommandType.STOP:
                request = ("GET", "/command/stop", {})
            case _:
                return

        drone = self.drones[node.id]
        method, path, kwargs = request
        drone.queue.put_nowait(lambda: drone.request(method, path, retry_for=COMMAND_RETRY_TIME, **kwargs))

    async def _finalize_report(self):
        """
        Reads the final battery levels, outputs a csv file with report information and logs a summary table.
        """
        def percentage(value, decimals=0):
            return "n/a" if value is None else f"{value:.{decimals}f}%"

        node_ids = list(self.drones)
        final_batteries = await asyncio.gather(*(self.drones[node_id].battery() for node_id in node_ids))

        csv_rows, table_rows = [], []
        for node_id, final_battery in zip(node_ids, final_batteries):
            entry = self._report[node_id]
            requests, drops, initial_battery = entry["telemetry_requests"], entry["telemetry_drops"], entry["initial_battery"]
            consumed = None
            if initial_battery is not None and final_battery is not None:
                consumed = float(initial_battery) - float(final_battery)

            csv_rows.append([node_id, requests, drops, "" if consumed is None else consumed])
            table_rows.append([
                str(node_id),
                str(requests),
                str(drops),
                percentage(100 * drops / requests if requests else None, decimals=2),
                percentage(initial_battery),
                percentage(final_battery),
                percentage(consumed),
            ])

        csv_path = os.path.abspath("ardupilot_mobility_report.csv")
        try:
            with open(csv_path, "w", newline="") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["node_id", "telemetry_requests", "telemetry_drops", "battery_wasted"])
                writer.writerows(csv_rows)
            saved_line = f"Report saved to {csv_path}"
        except Exception as e:
            saved_line = f"Could not save report to {csv_path}: {e}"

        headers = ["Node", "Telemetry updates", "Dropped", "Drop rate", "Battery start", "Battery end", "Consumed"]
        self._logger.info(f"{LOG_PREFIX} Mobility report\n{format_table(headers, table_rows)}\n{saved_line}")

    def _shutdown(self):
        """
        Cancels every task left in the asyncio loop and shuts down every Drone instance concurrently. A failure
        in one drone does not prevent the others from shutting down. Must only be called from synchronous code
        (initialize, finalize), where the asyncio loop is not running.
        """
        if self._shut_down or self._loop is None or self._loop.is_closed():
            return
        self._shut_down = True

        # Cancel any task still pending in the loop (drone startups, request consumers) so nothing is left dangling
        pending = asyncio.all_tasks(self._loop)
        for task in pending:
            task.cancel()
        self._run_all(pending, return_exceptions=True)

        results = self._run_all((drone.shutdown() for drone in self.drones.values()), return_exceptions=True)
        failed = 0
        for node_id, result in zip(self.drones, results):
            if isinstance(result, BaseException):
                failed += 1
                self._logger.error(f"{LOG_PREFIX} Error shutting down drone {node_id}: {result}")
            elif not result:
                failed += 1
                self._logger.warning(f"{LOG_PREFIX} Drone {node_id} shut down with errors")
            else:
                self._logger.info(f"{LOG_PREFIX} Drone {node_id} shut down")

        if failed == 0:
            self._logger.info(f"{LOG_PREFIX} All {len(self.drones)} drones shut down cleanly")
        else:
            self._logger.warning(f"{LOG_PREFIX} {failed} of {len(self.drones)} drones had shutdown errors")

    def _run_all(self, awaitables, return_exceptions=False) -> list:
        """
        Runs coroutines or tasks concurrently on the handler's asyncio loop and returns their results. Must only
        be called from synchronous code, where the loop is not running.
        """
        tasks = [self._loop.create_task(a) if asyncio.iscoroutine(a) else a for a in awaitables]
        if not tasks:
            return []
        return self._loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=return_exceptions))

    def finalize(self):
        """Ends simulation by finalizing report and shutting down drones."""
        try:
            if self._configuration.generate_report and not self._shut_down:
                self._loop.run_until_complete(
                    asyncio.wait_for(self._finalize_report(), timeout=REPORT_TIMEOUT))
        except Exception as e:
            self._logger.warning(f"Could not generate Ardupilot report: {e!r}")
        finally:
            self._shutdown()
