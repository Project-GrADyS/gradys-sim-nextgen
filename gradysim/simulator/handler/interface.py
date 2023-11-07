from abc import ABC, abstractmethod

from gradysim.simulator.event import EventLoop
from gradysim.simulator.node import Node


class INodeHandler(ABC):
    """
    The common interface every handler should implement.
    """

    @staticmethod
    @abstractmethod
    def get_label() -> str:
        """
        Static method returning the unique label of the handler. 
        If two handlers with the same label are registered only the last registered one will be accessible in the simulation.

        Returns:
            The unique label of this handler
        """
        pass

    @abstractmethod
    def inject(self, event_loop: EventLoop) -> None:
        """
        This function is called when the simulator is instantiated to provide the handler with the simulation's
        event loop.

        Args:
            event_loop: The simulation's event loop instance
        """
        pass

    def after_simulation_step(self, iteration: int, timestamp: float) -> None:
        """
        This callback function is called after every simulation step. Useful if the handler implements some 
        functionality that depends on running code at every step of the simulation.

        Args:
            iteration: Number of the iteration currently being ran
            timestamp: Current simulation timestamp in seconds
        """
        pass

    @abstractmethod
    def register_node(self, node: Node) -> None:
        """
        This is called after a node is added to the simulation's build process. The encapsulated node is
        passed as an argument.

        Args:
            node: Encapsulated node instance added to the simulation
        """
        pass

    def finalize(self) -> None:
        """
        This is called after the simulation is finished. Useful if the handler implements some functionality
        that depends on running code at the end of the simulation.
        """
        pass
