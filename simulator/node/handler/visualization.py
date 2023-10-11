from dataclasses import dataclass
from typing import List, Tuple

from matplotlib import pyplot as plt

from simulator.event import EventLoop
from simulator.node.handler.interface import INodeHandler
from simulator.node.node import Node


@dataclass
class VisualizationConfiguration:
    update_rate: float = 0.1
    x_range: Tuple[float, float] = (-50, 50)
    y_range: Tuple[float, float] = (-50, 50)
    z_range: Tuple[float, float] = (0, 50)


class VisualizationHandler(INodeHandler):
    _event_loop: EventLoop
    _nodes: List[Node]

    def __init__(self, configuration: VisualizationConfiguration = VisualizationConfiguration()):
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
