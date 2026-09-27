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
from typing import Dict, Tuple

from gradysim.protocol.messages.mobility import MobilityCommand, MobilityCommandType
from gradysim.protocol.messages.telemetry import Telemetry
from gradysim.protocol.position import Position
from gradysim.simulator.event import EventLoop
from gradysim.simulator.handler.interface import IAsyncNodeHandler
from gradysim.simulator.log import format_table
from gradysim.simulator.node import Node

from uav_api.run_api import spawn_with_args, run_with_args

SITL_SLEEP_TIME = 5
REPORT_TIMEOUT = 5
PROCESS_EXIT_TIMEOUT = 10
STARTUP_SITL_SPEEDUP = 10
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

class ArdupilotMobilityException(Exception):
    pass

@dataclass
class AsyncHttpResponse:
    status_code: int
    json: dict

class Drone:
    """
    Represents the Ardupilot version of the Node. This class maintains a co-routine
    that executes requests to UAV API to provide implementation for Mobility Commands
    and Telemetry updates. Each Node has an equivalent Drone instance.
    """

    _logger = None
    _request_consumer_task = None
    _request_queue = None
    _node_id = None
    _api_port = None
    _drone_url = None
    _api_process = None
    _session: aiohttp.ClientSession

    telemetry_requested = False
    position = None

    def __init__(self, node_id, initial_position, logger, api_port):
        """
        Sets base parameters for connection with UAV API as well as instantiate asyncio Queue,
        """
        self._logger = logger
        self._node_id = node_id
        self.telemetry_requested = False
        self._request_queue = asyncio.Queue()
        self._request_consumer_task = None
        self._api_port = api_port + self._node_id
        self._drone_url = f"http://localhost:{self._api_port}"
        self._session = None
        self._log_path = None

        self.position = initial_position

    async def get(self, url, params=None):
        """
        Performs an asynchronous HTTP GET request to the UAV API running on the port 
        defined on this instance.

        Args: 
            url: the path to be append after the domain
            params: dictionary of query parameters to be used in the request

        Returns:
            A co-routine of the HTTP request returning either HttpResponse if successfull or Exception if not
        """
        async with self._session.get(self._drone_url + url, params=params) as response:
            if response.status == 200:
                response_obj = AsyncHttpResponse(response.status, await response.json())
                return response_obj
            else:
                raise Exception(f"[DRONE-{self._node_id}] Failed to fetch data from {url}. Status code: {response.status}")

    async def post(self, url, json=None):
        """
        Performs an asynchronous HTTP POST request to the UAV API running on the port 
        defined on this instance.

        Args: 
            url: the path to be append after the domain
            json: dictionary of the parameters to be passed in the body of the request

        Returns:
            A co-routine of the HTTP request returning either HttpResponse if successfull or Exeception if not
        """
        async with self._session.post(self._drone_url + url, json=json) as response:
            if response.status == 200:
                response_obj = AsyncHttpResponse(response.status, await response.json())
                return response_obj
            else:
                raise Exception(f"Failed to post data to {url}. Status code: {response.status}")
    
    def request_telemetry(self):
        """
        Adds a telemetry update to the async request queue. Marks the telemetry_request flag as True.
        """
        self.telemetry_requested = True
        self.add_request(self.update_telemetry)

    async def update_telemetry(self):
        """
        Performs a telemetry update action by making an HTTP request to UAV API and then updating the
        instance position property. Finally, it marks the telemetry_requested flag as False.
        """
        telemetry_result = await self.get("/telemetry/ned")
        position = telemetry_result.json["info"]["position"]
        self.position = (position["x"], position["y"], -position["z"]) # translating NED frame to XYZ frame
        self.telemetry_requested = False

    def move_to_xyz(self, position: Position):
        """
        Schedules a movement command to a provided (x, y, z) value in the simulation frame. This request will be sent to UAV API by the request
        consumer of the instance

        Args:
            position: dictionary of XYZ coordinates of target waypoint
        """
        ned_position = {"x": position[0], "y": position[1], "z": -position[2]}
        self.add_request(lambda: self.post("/movement/go_to_ned", json=ned_position))

    def move_to_gps(self, lat, lon, alt):
        """
        Schedules a movement command to provided GPS coordinates. This request will be sent to UAV API by the request consumer of the instance
        
        Args:
            lat: latitude in degrees of the target waypoint
            lon: longitude in degrees of the target waypoint
            alt: altitude in meters of the target waypoint
        """

        gps_position = {"lat": lat, "long": lon, "alt": alt}
        self.add_request(lambda: self.post("/movement/go_to_gps", json=gps_position))

    def stop(self):
        """
        Scheduels a stop command to be sent to UAV API. This action will be executed by the request consumer of the instance
        """
        self.add_request(lambda: self.get("/command/stop"))

    def set_speed(self, speed: int):
        """
        Schedules a airspeed change command to be sent to UAV API. This action will be executed by the request consumer
        of the instance
        
        Args:
            speed: new airspeed value for vehicle. This velocity corresponds to the value of the norm of the velocity vector.
        """
        self.add_request(lambda: self.get("/command/set_air_speed", params={"new_v": speed}))

    def add_request(self, coro):
        """
        Adds an async fucntion to the request queue. Items on this queue are later removed and executedby the request
        consumer co-routine.

        Args:
            coro: asynchronous function that returns a co-routine. 
        """
        self._request_queue.put_nowait(coro)

    async def _request_consumer(self):
        """
        Pools co-routines from the request queue and awaits them. If the co-routine raises an Exception the loop logs it.
        """
        self._logger.debug(f"[ArdupilotMobilityHandler] Starting request consumer for node {self._node_id}")
        while True:
            request = await self._request_queue.get()
            self._logger.debug(f"[ArdupilotMobilityHandler] Processing request for node {self._node_id}")
            try:
                await request()
            except Exception as e:
                self._logger.debug(f"[ArdupilotMobilityHandler] Error handling request: {e}")
            self._request_queue.task_done()
        
    def set_session(self, session):
        """
        Set a new AsyncHttp session

        Args:
            session: AsyncHttp session instance
        """
        self._session = session

    def start_simulated_drone(self, uav_connection=None, sysid=None, ground_station_ip=None, ardupilot_path=None,
                              uav_api_log_path=None, log_console=False):
        """
        Starts UAV API simulated instance with base parameters. If log_console is False the process
        output is discarded, UAV API still writes its log file.
        """

        if uav_connection is None:
            uav_connection = f'127.0.0.1:17{171+self._node_id}'
        if sysid is None:
            sysid = self._node_id + 10

        raw_args = [
            '--simulated',
            '--headless',
            '--sysid', f'{sysid}', 
            '--port', f'{self._api_port}', 
            '--uav_connection', uav_connection, 
            '--speedup', str(STARTUP_SITL_SPEEDUP),
        ]

        if ground_station_ip is not None:
            raw_args.append("--gs_connection")
            raw_args.append(ground_station_ip)

        if ardupilot_path is not None:
            raw_args.append("--ardupilot_path")
            raw_args.append(ardupilot_path)
        
        if uav_api_log_path is not None:
            raw_args.append("--log_path")
            raw_args.append(uav_api_log_path)
            self._log_path = uav_api_log_path
        else:
            # Default log location used by UAV API
            self._log_path = os.path.expanduser(f"~/.uav_api/logs/uav_logs/uav_{sysid}.log")

        if log_console:
            self._api_process = spawn_with_args(raw_args)
        else:
            self._api_process = multiprocessing.Process(target=_run_uav_api_quietly, args=(raw_args,))
            self._api_process.start()

        time.sleep(5)

        if not self._api_process.is_alive():
            raise ArdupilotMobilityException(
                f"UAV API for drone {self._node_id} exited during startup "
                f"(exit code {self._api_process.exitcode}). See {self._log_path}")

    async def _set_sim_speedup(self, speedup: float):
        self._logger.debug(f"[DRONE-{self._node_id}] Setting simulation speedup to {speedup}...")
        await self.get("/command/set_sim_speedup", params={"sim_factor": speedup})
        self._logger.debug(f"[DRONE-{self._node_id}] Simulation speedup set to {speedup}.")

    async def goto_initial_position(self, sim_speedup: float = None):
        """
        Performs a series of requests to UAV API in order to drive the vehicle to the simulation
        starting point. Simulated vehicles are spawned with a sped up SITL, once the starting point
        is reached SITL is set to match the simulation's real-time factor.

        Args:
            sim_speedup: SITL speedup used during the simulation. None skips it (real vehicles)
        """
        self._logger.debug(f"[DRONE-{self._node_id}] Arming...")
        arm_result = await self.get("/command/arm")
        if arm_result.status_code != 200:
            raise ArdupilotMobilityException(f"[DRONE-{self._node_id}] Failed to arm drone.")
        self._logger.debug(f"[DRONE-{self._node_id}] Arming complete.")
        
        self._logger.debug(f"[DRONE-{self._node_id}] Taking off...")
        takeoff_result = await self.get("/command/takeoff", params={"alt": 10})
        if takeoff_result.status_code != 200:
            raise ArdupilotMobilityException(f"[DRONE-{self._node_id}] Failed to take off.")
        self._logger.debug(f"[DRONE-{self._node_id}] Takeoff complete.")

        self._logger.debug(f"[DRONE-{self._node_id}] Going to start position...")
        pos_data = {"x": self.position[0], "y": self.position[1], "z": -self.position[2]}
        go_to_result = await self.post("/movement/go_to_ned_wait", json=pos_data)
        if go_to_result.status_code != 200:
            raise ArdupilotMobilityException(f"[DRONE-{self._node_id}] Failed to go to start position.")
        self._logger.debug(f"[DRONE-{self._node_id}] Go to start position complete.")

        if sim_speedup is not None:
            await self._set_sim_speedup(sim_speedup)

        self._logger.debug(f"[DRONE-{self._node_id}] Starting request consumer task.")
        self._request_consumer_task = asyncio.create_task(self._request_consumer())
        
        await self.update_telemetry()

    async def get_battery_level(self):
        """
        Makes a battery level telemetry request to UAV API. If successfull returns battery level

        Returns:
            Remaining vehicle battery in percentage
        """
        battery_result = await self.get("/telemetry/battery_info")
        if battery_result.status_code != 200:
            return None
        return battery_result.json["info"]["battery_remaining"]
        
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
        self._logger.debug(f"[DRONE-{self._node_id}] Terminating drone UAV API process.")
        process.terminate()
        process.join(timeout)
        if process.is_alive():
            process.kill()
            process.join()
            self._logger.warning(f"{LOG_PREFIX} UAV API for drone {self._node_id} did not exit in {timeout}s and "
                                 f"was killed. SITL may still be running")
            return False
        self._logger.debug(f"[DRONE-{self._node_id}] UAV API process terminated.")
        return True

    async def shutdown(self) -> bool:
        """
        Terminates current co-routines and external process. This function should be called when
        the simulation has either finished or encountered an error.

        Returns:
            True if every shutdown step succeeded, False otherwise
        """
        clean = True
        self._logger.debug(f"[DRONE-{self._node_id}] Shutting down drone API and request consumer task.")
        try:
            if self._request_consumer_task:
                self._request_consumer_task.cancel()
                try:
                    await self._request_consumer_task
                except asyncio.CancelledError:
                    pass

            self._logger.debug(f"[DRONE-{self._node_id}] Request consumer task cancelled.")
        except Exception:
            clean = False
            self._logger.warning(f"[DRONE-{self._node_id}] Error cancelling request consumer task")
        
        if self._session is not None:
            self._logger.debug(f"[DRONE-{self._node_id}] Closing HTTP session.")
            try:
                await self._session.close()
                self._session = None
                self._logger.debug(f"[DRONE-{self._node_id}] HTTP session closed.")
            except Exception as e:
                clean = False
                self._logger.warning(f"[DRONE-{self._node_id}] Error closing HTTP session: {e}")

        try:
            # Runs in a thread so that drones wait for their processes in parallel
            clean = await asyncio.to_thread(self.terminate_process) and clean
        except Exception as e:
            clean = False
            self._logger.warning(f"[DRONE-{self._node_id}] Error terminating UAV API process: {e}")

        return clean

@dataclass
class ArdupilotMobilityConfiguration:
    """
    Configuration class for the Ardupilot mobility handler
    """

    update_rate: float = 0.5
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

    uav_api_log_console: bool = False
    """
    Whether to show UAV API and SITL output in the console. When False their output is discarded,
    UAV API still writes its log file (see uav_api_log_path). Used in simulated mode.
    """

    simulation_startup_speedup: int = 1
    """
    Multiplier for SITL simulation time. This value will only affect the setup of the simulation,
    after all drones are positioned in the right place and are ready to start, the simulation time
    goes back to matching real time.    
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
    _report: Dict[str, int]
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
        self._sitl_speedup = 1.0
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
            self._ardupilot_error("Error registering node: cannot register nodes while Ardupilot mobility handler "
                                    "is uninitialized.")
        
        self.drones[node.id] = Drone(node.id, node.position, self._logger, self._configuration.starting_api_port)
        
        if self._configuration.simulate_drones:
            self._logger.info(f"{LOG_PREFIX} Starting simulated drone {node.id} "
                              f"(UAV API on port {self.drones[node.id]._api_port})...")
            try:
                self.drones[node.id].start_simulated_drone(
                    ground_station_ip=self._configuration.ground_station_ip,
                    ardupilot_path=self._configuration.ardupilot_path,
                    uav_api_log_path=self._configuration.uav_api_log_path,
                    log_console=self._configuration.uav_api_log_console
                )
            except Exception as e:
                # The simulator is not finalized during build, so processes already spawned must be stopped here
                for drone in self.drones.values():
                    drone.terminate_process()
                self._ardupilot_error(f"Error starting drone {node.id}: {e}", cause=e)
        self.nodes[node.id] = node

    async def _initialize_report(self):
        """
        Initializes properties for tracking variables used in report
        """
        for node_id in self.nodes.keys():
            battery_level = await self._read_battery(node_id)
            if battery_level is None:
                self._logger.warning(f"{LOG_PREFIX} Could not read initial battery level of drone {node_id}, "
                                     f"battery consumption will be unavailable in the report")
            self._report[node_id] = {
                "initial_battery": battery_level,
                "telemetry_requests": 0,
                "telemetry_drops": 0
            }

    async def _read_battery(self, node_id):
        """
        Reads the battery level of a drone, returning None if it is unavailable
        """
        try:
            return await self.drones[node_id].get_battery_level()
        except Exception as e:
            self._logger.debug(f"Error fetching battery level for node {node_id}: {e}")
            return None

    async def _initialize_drones(self):
        """
        Sends each drone to the starting position through the goto_initial_position routine.
        Each drone has it's own routine and they run concurrently.
        """
        for node_id in self.nodes.keys():
            http_session = aiohttp.ClientSession()
            drone = self.drones[node_id]
            drone.set_session(http_session)

        if self._configuration.simulate_drones:
            self._logger.info(f"{LOG_PREFIX} Waiting for {len(self.drones)} UAV API instances to be ready...")
            time.sleep(SITL_SLEEP_TIME) # Wait for API process to start
            sim_speedup = self._sitl_speedup
        else:
            # Real vehicles cannot be sped up
            sim_speedup = None

        drone_init_tasks = []
        for node_id in self.nodes.keys():
            drone_init_tasks.append(asyncio.create_task(
                self.drones[node_id].goto_initial_position(sim_speedup)))
        
        try:
            await asyncio.gather(*drone_init_tasks)  
        except Exception as e:
            # gather does not cancel sibling tasks on failure, so we do it ourselves
            for task in drone_init_tasks:
                task.cancel()
            await asyncio.gather(*drone_init_tasks, return_exceptions=True)
            self._ardupilot_error(f"Error initializing drones: {e}", cause=e)

        for node_id, drone in self.drones.items():
            position = tuple(round(coordinate, 2) for coordinate in drone.position)
            speedup_info = f", SITL speedup {self._sitl_speedup:g}x" if sim_speedup not in (None, 1) else ""
            self._logger.info(f"{LOG_PREFIX} Drone {node_id} ready (UAV API on port {drone._api_port}, "
                              f"at initial position {position}{speedup_info})")
        self._logger.info(f"{LOG_PREFIX} All {len(self.drones)} drones initialized")
    
    def initialize(self):
        if self._loop is None:
            raise ArdupilotMobilityException("No async loop provided. inject_async was never called")

        if self._real_time <= 0:
            self._logger.warning(f"{LOG_PREFIX} The simulation is not running in real-time mode. SITL runs on the "
                                 f"wall clock, so the simulation will diverge from it. Enable real_time in "
                                 f"SimulationConfiguration")
            self._sitl_speedup = 1.0
        else:
            self._sitl_speedup = self._real_time

        if not self._configuration.simulate_drones and self._real_time not in (0, 1):
            self._logger.warning(f"{LOG_PREFIX} Real vehicles cannot be sped up, the simulation running at "
                                 f"{self._real_time:g}x real time will diverge from them")

        try:
            self._loop.run_until_complete(self._initialize_drones())
            if self._configuration.generate_report:
                self._loop.run_until_complete(self._initialize_report())
        except Exception:
            self._shutdown_sync()
            raise
        self._setup_telemetry()     

    async def _shutdown(self):
        """
        Shuts down every Drone instance concurrently. A failure in one drone does not
        prevent the others from shutting down.
        """
        self._shut_down = True
        node_ids = list(self.drones.keys())
        results = await asyncio.gather(*(self.drones[node_id].shutdown() for node_id in node_ids),
                                       return_exceptions=True)
        failed = 0
        for node_id, result in zip(node_ids, results):
            if isinstance(result, BaseException):
                failed += 1
                self._logger.error(f"{LOG_PREFIX} Error shutting down drone {node_id}: {result}")
            elif not result:
                failed += 1
                self._logger.warning(f"{LOG_PREFIX} Drone {node_id} shut down with errors")
            else:
                self._logger.info(f"{LOG_PREFIX} Drone {node_id} shut down")

        if failed == 0:
            self._logger.info(f"{LOG_PREFIX} All {len(node_ids)} drones shut down cleanly")
        else:
            self._logger.warning(f"{LOG_PREFIX} {failed} of {len(node_ids)} drones had shutdown errors")

        # Cancel any task still pending in the loop so nothing is left dangling
        current_task = asyncio.current_task()
        pending = [task for task in asyncio.all_tasks() if task is not current_task]
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)

    def _shutdown_sync(self):
        """
        Synchronous entry point for shutdown. Must only be called from synchronous boundaries
        (initialize, finalize) where the asyncio loop is guaranteed not to be running.
        """
        if self._shut_down or self._loop is None or self._loop.is_closed():
            return
        self._loop.run_until_complete(self._shutdown())

    def _ardupilot_error(self, message, cause: Exception = None):
        """
        Logs an error message and raises an ArdupilotMobilityException. This function
        should be called when an error has ocurred in the connection with UAV API. It
        does not clean anything up by itself: the exception propagates to initialize or
        finalize, which are responsible for shutting down Drone instances. Because of this
        it can be safely called from both synchronous and asynchronous contexts.

        Args:
            message: the message to be printed
            cause: optional exception that originated the error, chained to the raised exception
        """
        self._logger.error(message)
        raise ArdupilotMobilityException(message) from cause

    def _setup_telemetry(self):
        """
        Initiates a recorrent telemetry event at a fixed rate for each node. Every time the event
        fires, it checks if the last position information was updated. If not, it simply skips.
        If it was updated, it calls handle_telemetry method of the corresponding node and requests
        a new telemetry update.
        """
        def send_telemetry(node_id):
            node = self.nodes[node_id]
            drone = self.drones[node_id]

            if self._configuration.generate_report:
                self._report[node_id]["telemetry_requests"] += 1
            if not drone.telemetry_requested:
                node.position = drone.position
                telemetry = Telemetry(current_position=node.position)
                node.protocol_encapsulator.handle_telemetry(telemetry)
                self._logger.debug(f"Telemetry sent for node {node_id}. Value")
                drone.request_telemetry()
                self._logger.debug(f"Telemetry requested for node {node_id}.")
            else:
                if self._configuration.generate_report:
                    self._report[node_id]["telemetry_drops"] += 1
                self._logger.debug(f"Telemetry already requested for node {node_id}, skipping.")

            
            self._event_loop.schedule_event(self._event_loop.current_time + self._configuration.update_rate,
                                    make_send_telemetry(node_id), "ArdupilotMobility")
        
        def make_send_telemetry(node_id):
            return lambda: send_telemetry(node_id)

        for node_id in self.nodes.keys():
            self._event_loop.schedule_event(self._event_loop.current_time,
                    make_send_telemetry(node_id), "ArdupilotMobility")

    def handle_command(self, command: MobilityCommand, node: Node):
        """
        Performs a mobility command in the SITL-based simulation. This method is called
        by the node's provider to transmit it's mobility command to the ardupilot mobility
        handler and then to the node's UAV API.

        Args:
            command: Command being issued
            node: Node that issued the command
        """
        drone = self.drones[node.id]
        self._logger.debug(f"Handling command: {command.command_type}, {command.param_1}, {command.param_2}, {command.param_3}")
        if node.id not in self.nodes:
            self._ardupilot_error("Error handling commands: Cannot handle command from unregistered node")

        if command.command_type == MobilityCommandType.GOTO_COORDS:
            drone.move_to_xyz((command.param_1, command.param_2, command.param_3))
        elif command.command_type == MobilityCommandType.GOTO_GEO_COORDS:
            drone.move_to_gps(command.param_1, command.param_2, command.param_3)
        elif command.command_type == MobilityCommandType.SET_SPEED:
            drone.set_speed(command.param_1)
        elif command.command_type == MobilityCommandType.STOP:
            drone.stop()

    async def _finalize_report(self):
        """
        Ends report tracking, outputs a csv file with report information and logs a summary table.
        """
        for node_id in self.nodes.keys():
            self._report[node_id]["final_battery"] = await self._read_battery(node_id)

        csv_path = os.path.abspath("ardupilot_mobility_report.csv")
        try:
            with open(csv_path, "w", newline="") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["node_id", "telemetry_requests", "telemetry_drops", "battery_wasted"])
                for node_id in self.nodes.keys():
                    entry = self._report[node_id]
                    consumed = self._battery_consumed(entry)
                    writer.writerow([node_id, entry["telemetry_requests"], entry["telemetry_drops"],
                                     "" if consumed is None else consumed])
            saved_line = f"Report saved to {csv_path}"
        except Exception as e:
            saved_line = f"Could not save report to {csv_path}: {e}"

        self._logger.info(f"{LOG_PREFIX} Mobility report\n{self._format_report_table()}\n{saved_line}")

    @staticmethod
    def _battery_consumed(entry):
        initial_battery = entry.get("initial_battery")
        final_battery = entry.get("final_battery")
        if initial_battery is None or final_battery is None:
            return None
        return float(initial_battery) - float(final_battery)

    def _format_report_table(self) -> str:
        """
        Formats the report of every drone as an aligned text table
        """
        def percentage(value, decimals=0):
            return "n/a" if value is None else f"{value:.{decimals}f}%"

        headers = ["Node", "Telemetry updates", "Dropped", "Drop rate", "Battery start", "Battery end", "Consumed"]
        rows = []
        for node_id in self.nodes.keys():
            entry = self._report[node_id]
            requests = entry["telemetry_requests"]
            drops = entry["telemetry_drops"]
            rows.append([
                str(node_id),
                str(requests),
                str(drops),
                percentage(100 * drops / requests if requests else None, decimals=2),
                percentage(entry.get("initial_battery")),
                percentage(entry.get("final_battery")),
                percentage(self._battery_consumed(entry)),
            ])

        return format_table(headers, rows)

    def finalize(self):
        """Ends simulation by finalizing report and shutting down drones."""
        try:
            if self._configuration.generate_report and not self._shut_down:
                self._loop.run_until_complete(
                    asyncio.wait_for(self._finalize_report(), timeout=REPORT_TIMEOUT))
        except Exception as e:
            self._logger.warning(f"Could not generate Ardupilot report: {e!r}")
        finally:
            self._shutdown_sync()