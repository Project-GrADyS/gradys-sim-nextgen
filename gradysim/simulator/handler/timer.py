from gradysim.simulator.event import EventLoop
from gradysim.simulator.node import Node
from gradysim.simulator.handler.interface import INodeHandler


class TimerException(Exception):
    pass


class TimerHandler(INodeHandler):
    """
    Adds timers to the simulation. This allows nodes to set timers
    which is a very important feature when implementing distributed
    algorithms. Nodes can schedule timers through their providers.
    """
    _event_loop: EventLoop

    def __init__(self):
        """
        Constructs a TimerHandler, no configuration is necessary.
        """
        self._registed_nodes: set[Node] = set()

    def get_current_time(self):
        return self._event_loop.current_time

    @staticmethod
    def get_label() -> str:
        return "timer"

    def inject(self, event_loop: EventLoop) -> None:
        self._event_loop = event_loop

    def register_node(self, node: Node) -> None:
        self._registed_nodes.add(node)

    def set_timer(self, message: str, timestamp: float, node: Node):
        """
        Sets a timer. Should be called by the nodes' providers. Node needs to be
        registered and timer needs to be set in the future.
        """
        if node not in self._registed_nodes:
            raise TimerException(f"Could not set timer: Node {node.id} not registered")

        if timestamp < self._event_loop.current_time:
            raise TimerException("Could not set timer: Timer cannot be set in the past")

        self._event_loop.schedule_event(timestamp,
                                        lambda: node.protocol_encapsulator.handle_timer(message),
                                        f"Node {node.id}")
