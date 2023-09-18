from abc import ABC, abstractmethod

from simulator.node import Node


class INodeHandler(ABC):
    @abstractmethod
    def register_node(self, node: Node):
        pass