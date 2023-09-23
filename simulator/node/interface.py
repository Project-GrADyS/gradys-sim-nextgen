from abc import ABC, abstractmethod

from simulator.event.loop import EventLoop
from simulator.node import Node


class INodeHandler(ABC):
    @abstractmethod
    def inject(self, event_loop: EventLoop):
        pass

    @abstractmethod
    def register_node(self, node: Node):
        pass
