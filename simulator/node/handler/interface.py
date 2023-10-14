from abc import ABC, abstractmethod

from simulator.event import EventLoop
from simulator.node.node import Node


class INodeHandler(ABC):
    @staticmethod
    @abstractmethod
    def get_label() -> str:
        pass

    @abstractmethod
    def inject(self, event_loop: EventLoop) -> None:
        pass

    def after_simulation_step(self, iteration: int, timestamp: float):
        pass

    @abstractmethod
    def register_node(self, node: Node) -> None:
        pass
