from simulator.event import EventLoop
from simulator.node import Node
from simulator.node.interface import INodeHandler


class TimerHandler(INodeHandler):
    _event_loop: EventLoop

    def get_label(self) -> str:
        return "timer"

    def inject(self, event_loop: EventLoop) -> None:
        self._event_loop = event_loop

    def register_node(self, node: Node) -> None:
        pass

    def set_timer(self, message: str, timestamp: float, node: Node):
        self._event_loop.schedule_event(timestamp, lambda: node.protocol_encapsulator.handle_timer(message))