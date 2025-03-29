"""
This handler adds visualization to the simulation. It shows regularly updated node positions in a graphical
representation of the simulation. This graphical representation is web-based and can be accessed via a browser
through [this link](https://project-gradys.github.io/gradys-sim-nextgen-visualization/). When the simulation starts running
a WebSocket server is started which the browser connects to. The browser then displays the simulation in a 3D
environment. The visualization is updated regularly with the current node positions and other information.

!!!danger
    The visualization handler uses a separate process to run the WebSocket server, this means that on Windows your
    script will be rerun when the new process starts. This means that any code that should not be run multiple times
    should be put in the `if __name__ == "__main__"` block.
"""

import asyncio
import json
import logging
import multiprocessing
import time
import webbrowser
from dataclasses import dataclass
from typing import List, Tuple, TypedDict, Literal

import websockets

from gradysim.protocol.position import Position
from gradysim.simulator.event import EventLoop
from gradysim.simulator.handler.interface import INodeHandler
from gradysim.simulator.log import label_node
from gradysim.simulator.node import Node


@dataclass
class VisualizationConfiguration:
    """
    Configuration for the VisualizationHandler
    """

    information_collection_interval: float = 0.01
    """
    Interval in simulation seconds between visualization information update. Beware that this is not the frequency
    at which the visualization is updated in the browser, but the frequency at which data is collected from the 
    running simulation. You can change the broser update frequency with the `update_rate` parameter.
    """

    update_rate: float = 0.05
    """
    Rate in seconds at which the visualization is updated in the browser. This is the frequency at which the browser
    receives the information from the simulation.
    """

    x_range: Tuple[float, float] = (-50, 50)
    """Range of the X axis of the visualization in meters"""

    y_range: Tuple[float, float] = (-50, 50)
    """Range of the Y axis of the visualization in meters"""

    z_range: Tuple[float, float] = (0, 50)
    """Range of the Z axis of the visualization in meters"""

    host: str = "localhost"
    """Host address of the visualization server"""

    port: int = 5678
    """Port that the visualization server will run in"""

    open_browser: bool = False
    """Whether to open the browser automatically when the simulation starts"""


class _InitializationInformation(TypedDict):
    x_range: Tuple[float, float]
    y_range: Tuple[float, float]
    z_range: Tuple[float, float]
    nodes: List[str]


class _VisualizationInformation(TypedDict):
    nodes: List[int]
    positions: List[Position]
    simulation_time: float
    real_time: float
    tracked_variables: List[dict]


class _VisualizationCommand(TypedDict):
    command: Literal["paint_node", "paint_environment", "resize_nodes"]
    payload: dict


class _VisualizationState(TypedDict):
    # Set by the visualization thread, pauses the simulation if set to True
    paused: bool


class _VisualizationMessage(TypedDict):
    interaction: Literal["pause/resume"]


class VisualizationHandler(INodeHandler):
    """
    Adds visualization to the simulation. Shows regularly updated node position and other simulation information
    in a graphical representation of the simulation. The graphical representation is web-based and can be accessed
    via a browser through [this link](https://project-gradys.github.io/gradys-sim-nextgen-visualization/).

    The visualization handler uses a separate process to run the WebSocket server, on Windows your
    script will be rerun when the new process starts. This means that any code that should not be run multiple times
    should be put in the `if __name__ == "__main__"` block.
    """
    _event_loop: EventLoop
    _nodes: List[Node]
    _information: _VisualizationInformation
    _visualization_state: _VisualizationState
    _information_thread: multiprocessing.Process
    _start_time: float
    command_queue: multiprocessing.Queue

    def __init__(self, configuration: VisualizationConfiguration = VisualizationConfiguration()):
        """
        Constructs the visualization handler.

        Args:
            configuration: Configuration for the visualization handler. If not set all default values will be used.
        """
        self._nodes = []

        # Current simulation information shared with the visualization server
        manager = multiprocessing.Manager()
        self._information = manager.dict()
        self._visualization_state = manager.dict()
        self.command_queue = manager.Queue()
        self._visualization_state["paused"] = False

        self._configuration = configuration

        self._logger = logging.getLogger()

        global _active_handler
        _active_handler = self

    @staticmethod
    def get_label() -> str:
        return "visualization"

    def inject(self, event_loop: EventLoop) -> None:
        self._event_loop = event_loop

        self._event_loop.schedule_event(self._event_loop.current_time + self._configuration.information_collection_interval,
                                        self._report_information,
                                        "Visualization")

    def initialize(self) -> None:
        initialization_information = {
            "x_range": self._configuration.x_range,
            "y_range": self._configuration.y_range,
            "z_range": self._configuration.z_range,
            "nodes": [label_node(node) for node in self._nodes],
        }

        # Initialize with precise CPU timestamp of simulation's start
        # does not use event loop
        self._start_time = time.time()

        self._information_thread = multiprocessing.Process(target=_visualization_thread,
                                                           args=(self._configuration,
                                                                 initialization_information,
                                                                 self._information,
                                                                 self._visualization_state,
                                                                 self.command_queue))
        self._information_thread.start()

    def finalize(self) -> None:
        self._information_thread.terminate()

    def register_node(self, node: Node) -> None:
        self._nodes.append(node)

    def _report_information(self) -> None:
        self._information["nodes"] = [node.id for node in self._nodes]
        self._information["positions"] = [node.position for node in self._nodes]
        self._information["simulation_time"] = self._event_loop.current_time
        self._information["real_time"] = time.time() - self._start_time
        self._information["tracked_variables"] = \
            [node.protocol_encapsulator.protocol.provider.tracked_variables.copy() for node in self._nodes]

        if self._visualization_state["paused"]:
            logging.info("Visualization paused by user")

            while self._visualization_state["paused"]:
                time.sleep(0.1)

            logging.info("Visualization resumed by user")

        self._event_loop.schedule_event(
            self._event_loop.current_time + self._configuration.information_collection_interval,
            self._report_information,
            "Visualization"
        )


def _visualization_thread(config: VisualizationConfiguration,
                          init_data: _InitializationInformation,
                          information: _VisualizationInformation,
                          state: _VisualizationState,
                          command_queue: multiprocessing.Queue) -> None:
    """
    Visualization server thread that runs the WebSocket server and broadcasts the simulation information to
    connected clients.

    Args:
        config: Visualization handler's configuration
        init_data: Initial information about the simulation to send to the client
        information: Current information about the simulation to send to the client
        state: Current state of the visualization
        command_queue: Queue of commands to execute in the visualization
    """
    websocket_connections = set()

    async def register(websocket: websockets.WebSocketServerProtocol):
        websocket_connections.add(websocket)
        try:
            await websocket.send(json.dumps(init_data.copy()))

            async for message in websocket:
                data: _VisualizationMessage = json.loads(message)
                if data["interaction"] == "pause/resume":
                    state["paused"] = not state["paused"]

            await websocket.wait_closed()
        finally:
            websocket_connections.remove(websocket)

    async def update_information():
        while True:
            websockets.broadcast(websocket_connections, json.dumps(information.copy()))

            while not command_queue.empty():
                command: _VisualizationCommand = command_queue.get()
                websockets.broadcast(websocket_connections, json.dumps(command))

            await asyncio.sleep(config.update_rate)

    async def main():
        async with websockets.serve(register, config.host, config.port):
            if config.open_browser:
                webbrowser.open("https://project-gradys.github.io/gradys-sim-nextgen-visualization/")

            await update_information()

    asyncio.run(main())