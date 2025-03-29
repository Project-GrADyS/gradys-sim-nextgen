from typing import Tuple, Optional

from gradysim.protocol.interface import IProtocol
from gradysim.simulator.extension.extension import Extension
from gradysim.simulator.handler.visualization import VisualizationHandler


class VisualizationController(Extension):
    """
    Controller for the visualization handler. Can be used to send commands to the visualization handler from a
    protocol. Commands can be used to affect the visualization, such as painting nodes or changing the
    environment's color.

    !!!info
        Every method in this class is a no-op if a visualization handler is not active. This includes when the protocol is
        not running on a python simulation environment.

    !!!warning
        This class is an [extension][gradysim.simulator.extension] and will raise an error if the protocol is not
        running on a python simulation.
    """
    def __init__(self, protocol: IProtocol):
        super().__init__(protocol)
        if self._provider is not None:
            self._visualization_handler: Optional[VisualizationHandler] = \
                self._provider.handlers.get("visualization") if self._provider is not None else None

    def paint_node(self, node_id: int, color: Tuple[float, float, float]) -> None:
        """
        Paints a node in the visualization with a specific color.

        Args:
            node_id: ID of the node to paint
            color: RGB color of the node
        """
        if self._visualization_handler is None:
            return

        self._visualization_handler.command_queue.put({
            "command": "paint_node",
            "payload": {
                "node_id": node_id,
                "color": color
            }
        })

    def paint_environment(self, color: Tuple[float, float, float]) -> None:
        """
        Paints the environment in the visualization with a specific color.

        Args:
            color: RGB color of the environment
        """
        if self._visualization_handler is None:
            return

        self._visualization_handler.command_queue.put({
            "command": "paint_environment",
            "payload": {
                "color": color
            }
        })

    def resize_nodes(self, size: float) -> None:
        """
        Resizes the nodes in the visualization
        Args:
            size: New size of the nodes
        """
        if self._visualization_handler is None:
            return

        self._visualization_handler.command_queue.put({
            "command": "resize_nodes",
            "payload": {
                "size": size
            }
        })

    def show_node_id(self, node_id: int, show: bool):
        """
        Paints or unpaints the node_id text over the node.
        Args:
            node_id: ID of the node
            show: wheter to show the node_id or not
        """
        if self._visualization_handler is None:
            return

        self._visualization_handler.command_queue.put({
            "command": "show_node_id",
            "payload": {
                "node_id": node_id,
                "show": show,
            }
        })