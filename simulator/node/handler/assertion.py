from abc import abstractmethod
from typing import Type, List, Callable, TypeVar

from simulator.event import EventLoop
from simulator.node.handler.interface import INodeHandler
from simulator.node.node import Node
from simulator.protocols.interface import IProtocol


class FailedAssertionException(Exception):
    pass


class SimulationTestCase:
    @abstractmethod
    def test_iteration(self, nodes: List[Node], iteration: int, timestamp: float) -> None:
        pass

    @abstractmethod
    def finalize(self):
        pass


P = TypeVar("P", bound=IProtocol)


def assert_always_true_for_protocol(func: Callable[[Node[P]], bool],
                                    protocol_type: Type[P],
                                    name: str = None,
                                    description: str = "") -> Type[SimulationTestCase]:
    if name is None:
        name = func.__name__

    class TestCase(SimulationTestCase):
        def test_iteration(self, nodes: List[Node[P]], iteration: int, timestamp: float):
            for node in nodes:
                if isinstance(node.protocol_encapsulator.protocol, protocol_type):
                    if not func(node):
                        raise FailedAssertionException(f"Assertion \"{name}\" {'(' + description + ') '}failed "
                                                       f"[iteration={iteration} | timestamp={timestamp}]")

        def finalize(self):
            pass

    return TestCase


def assert_eventually_true_for_protocol(func: Callable[[Node], bool],
                                        protocol_type: Type[IProtocol],
                                        name: str = None,
                                        description: str = "") -> Type[SimulationTestCase]:
    if name is None:
        name = func.__name__

    class TestCase(SimulationTestCase):
        has_been_true = False

        def test_iteration(self, nodes: List[Node], iteration: int, timestamp: float):
            for node in nodes:
                if isinstance(node.protocol_encapsulator.protocol, protocol_type):
                    if func(node):
                        self.has_been_true = True

        def finalize(self):
            if not self.has_been_true:
                raise FailedAssertionException(f"Assertion \"{name}\" {'(' + description + ') '}failed\n"
                                               f"The condition was never met during the simulation")

    return TestCase


def assert_always_true_for_simulation(func: Callable[[List[Node]], bool],
                                      name: str = None,
                                      description: str = "") -> Type[SimulationTestCase]:
    if name is None:
        name = func.__name__

    class TestCase(SimulationTestCase):
        def test_iteration(self, nodes: List[Node], iteration: int, timestamp: float):
            if not func(nodes):
                raise FailedAssertionException(f"Assertion \"{name}\" {'(' + description + ') '}failed\n"
                                               f"[iteration={iteration} | timestamp={timestamp}]\n")

        def finalize(self):
            pass

    return TestCase


def assert_eventually_true_for_simulation(func: Callable[[List[Node]], bool],
                                          name: str = None,
                                          description: str = "") -> Type[SimulationTestCase]:
    if name is None:
        name = func.__name__

    class TestCase(SimulationTestCase):
        has_been_true = False

        def test_iteration(self, nodes: List[Node], iteration: int, timestamp: float):
            if func(nodes):
                self.has_been_true = True

        def finalize(self):
            if not self.has_been_true:
                raise FailedAssertionException(f"Assertion \"{name}\" {'(' + description + ') '}failed\n"
                                               f"The condition was never met during the simulation")

    return TestCase


class AssertionHandler(INodeHandler):
    _event_loop: EventLoop
    _nodes: List[Node]

    def __init__(self, assertions: List[Type[SimulationTestCase]]):
        self._assertions = [assertion() for assertion in assertions]
        self._nodes = []

    @staticmethod
    def get_label() -> str:
        return "assertion"

    def inject(self, event_loop: EventLoop) -> None:
        self._event_loop = event_loop

    def register_node(self, node: Node) -> None:
        self._nodes.append(node)

    def after_simulation_step(self, iteration: int, timestamp: float):
        for assertion in self._assertions:
            assertion.test_iteration(self._nodes, iteration, timestamp)

    def finalize(self):
        for assertion in self._assertions:
            assertion.finalize()
