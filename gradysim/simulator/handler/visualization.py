from dataclasses import dataclass
from typing import List, Tuple

from matplotlib import pyplot as plt

from gradysim.simulator.event import EventLoop
from gradysim.simulator.handler.interface import INodeHandler
from gradysim.simulator.node import Node


@dataclass
class VisualizationConfiguration:
    """
    Configuration for the VisualizationHandler
    """

    update_rate: float = 0.5
    """Interval in simulation seconds between visualization updates"""

    x_range: Tuple[float, float] = (-50, 50)
    """Range of the X axis of the visualization in meters"""

    y_range: Tuple[float, float] = (-50, 50)
    """Range of the Y axis of the visualization in meters"""

    z_range: Tuple[float, float] = (0, 50)
    """Range of the Z axis of the visualization in meters"""


class VisualizationHandler(INodeHandler):
    """
    Adds visualization to the simulation. Shows regularly updated node position in a graphical
    representation of the simulation. Providers don't interact with this assertion handler,
    it only consults every nodes' position to update the visualization.
    """
    _event_loop: EventLoop
    _nodes: List[Node]

    def __init__(self, configuration: VisualizationConfiguration = VisualizationConfiguration()):
        """
        Constructs the visualization handler.

        Args:
            configuration: Configuration for the visualization handler. If not set all default values will be used.
        """
        self._nodes = []
        self._configuration = configuration

    @staticmethod
    def get_label() -> str:
        return "visualization"

    def inject(self, event_loop: EventLoop) -> None:
        self._event_loop = event_loop

        self._initialize_plot()
        self._event_loop.schedule_event(self._event_loop.current_time + self._configuration.update_rate,
                                        self._update_plot,
                                        "Visualization")

    def register_node(self, node: Node) -> None:
        self._nodes.append(node)

    def _initialize_plot(self):
        plt.ion()
        plt.show()

        # Initialize the figure and 3D axes
        self._fig = plt.figure()
        self._ax = self._fig.add_subplot(111, projection='3d')
        self._ax.set_xlim(*self._configuration.x_range)
        self._ax.set_ylim(*self._configuration.y_range)
        self._ax.set_zlim(*self._configuration.z_range)

    def _update_plot(self):
        plt.cla()
        self._ax.scatter(
            [node.position[0] for node in self._nodes],
            [node.position[1] for node in self._nodes],
            [node.position[2] for node in self._nodes]
        )
        self._ax.set_xlim(*self._configuration.x_range)
        self._ax.set_ylim(*self._configuration.y_range)
        self._ax.set_zlim(*self._configuration.z_range)
        plt.draw()
        plt.pause(0.001)

        self._event_loop.schedule_event(self._event_loop.current_time + self._configuration.update_rate,
                                        self._update_plot,
                                        "Visualization")
