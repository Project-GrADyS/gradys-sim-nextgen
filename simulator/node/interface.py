from abc import ABC, abstractmethod

from simulator.event import EventLoop
from simulator.node import Node


class INodeHandler(ABC):
    @abstractmethod
    def get_label(self) -> str:
        pass

    @abstractmethod
    def inject(self, event_loop: EventLoop) -> None:
        pass

    @abstractmethod
    def register_node(self, node: Node) -> None:
        pass
