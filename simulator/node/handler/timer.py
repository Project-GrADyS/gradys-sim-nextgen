from simulator.event import EventLoop
from simulator.node import Node
from simulator.node.interface import INodeHandler


class TimerException(Exception):
    pass


class TimerHandler(INodeHandler):
    _event_loop: EventLoop

    def __init__(self):
        self._registed_nodes: set[Node] = set()

    def get_current_time(self):
        return self._event_loop.current_time

    def get_label(self) -> str:
        return "timer"

    def inject(self, event_loop: EventLoop) -> None:
        self._event_loop = event_loop

    def register_node(self, node: Node) -> None:
        self._registed_nodes.add(node)

    def set_timer(self, message: str, timestamp: float, node: Node):
        if node not in self._registed_nodes:
            raise TimerException(f"Could not set timer: Node {node.id} not registered")

        self._event_loop.schedule_event(timestamp, lambda: node.protocol_encapsulator.handle_timer(message))
