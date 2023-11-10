from abc import abstractmethod
from typing import Type, List, Callable, TypeVar, Dict

from gradysim.protocol.interface import IProtocol
from gradysim.simulator.event import EventLoop
from gradysim.simulator.handler.interface import INodeHandler
from gradysim.simulator.node import Node


class FailedAssertionException(Exception):
    pass


class SimulationTestCase:
    """
    Generic test case. Is called at avery simulation iteration with the list of nodes,
    iteration and timestamp, and when the simulation is finalized. Should raise a 
    FailedAssertionException to indicate that the test case has failed.
    """
    @abstractmethod
    def test_iteration(self, nodes: List[Node], iteration: int, timestamp: float) -> None:
        pass

    @abstractmethod
    def finalize(self):
        pass


P = TypeVar("P", bound=IProtocol)


def assert_always_true_for_protocol(protocol_type: Type[P],
                                    name: str,
                                    description: str = "") -> Callable[[], Type[SimulationTestCase]]:
    """
    Creates a decorator that will wrap any function receiving a Node and returning a boolean into a
    assertion. If at any point the function returns False the assertion will fail.

    The assertion function should recieve a single Node instance with a specific protocol type and 
    return True if the assertion is succesfull and False otherwise.

     Function should be of type `Callable[[Node], bool]`.

    Args:
        protocol_type: Type of protocol that this assertion applies to. Will be called for every node of that type.
        name: Name of the assertion, used to identify the assertion
        description: Optional description used in logging
    """
    def decorator(func: Callable[[Node[P]], bool]) -> Type[SimulationTestCase]:
        nonlocal name
        if name is None:
            name = func.__name__

        class TestCase(SimulationTestCase):
            def test_iteration(self, nodes: List[Node[P]], iteration: int, timestamp: float):
                for node in nodes:
                    if isinstance(node.protocol_encapsulator.protocol, protocol_type):
                        if not func(node):
                            description_string = "(" + description + ") " if description != "" else ""
                            raise FailedAssertionException(f"Assertion \"{name}\" {description_string}failed "
                                                           f"[iteration={iteration} | timestamp={timestamp}]")

            def finalize(self):
                pass

        return TestCase

    return decorator


def assert_eventually_true_for_protocol(protocol_type: Type[IProtocol],
                                        name: str,
                                        description: str = "") -> Callable[[], Type[SimulationTestCase]]:
    """
    Creates a decorator that will wrap any function receiving a Node and returning a boolean into a
    assertion. If at any point in the simulation the function returns True for a node the assertion
    will succeed for that node.

    The assertion function should recieve a single Node instance with a specific protocol type and 
    return True if the assertion is succesfull and False otherwise.

    Function should be of type `Callable[[Node], bool]`.

    Args:
        protocol_type: Type of protocol that this assertion applies to. Will be called for every node of that type.
        name: Name of the assertion, used to identify the assertion
        description: Optional description used in logging
    """
    
    def decorator(func: Callable[[Node], bool]) -> Type[SimulationTestCase]:
        nonlocal name
        if name is None:
            name = func.__name__

        class TestCase(SimulationTestCase):
            has_been_true: Dict[int, bool]

            def __init__(self):
                self.has_been_true = {}

            def test_iteration(self, nodes: List[Node], iteration: int, timestamp: float):
                for node in nodes:
                    if isinstance(node.protocol_encapsulator.protocol, protocol_type):
                        if node.id not in self.has_been_true:
                            self.has_been_true[node.id] = False
                        if func(node):
                            self.has_been_true[node.id] = True

            def finalize(self):
                for node, has_been in self.has_been_true.items():
                    if not has_been:
                        description_string = "(" + description + ") " if description != "" else ""
                        raise FailedAssertionException(
                            f"Assertion \"{name}\" {description_string} failed in node {node}\n"
                            f"The condition was never met during the simulation")

        return TestCase

    return decorator


def assert_always_true_for_simulation(name: str,
                                      description: str = "") -> Callable[[], Type[SimulationTestCase]]:
    """
    Creates a decorator that will wrap any function receiving all Nodes and returning a boolean into a
    assertion. If at any point in the simulation this function returns False, the assertion fails.

    The assertion function should recieve a Node list and return True if the assertion is succesfull 
    and False otherwise.

    Function should be of type `Callable[[List[Node]], bool]`.

    Args:
        name: Name of the assertion, used to identify the assertion
        description: Optional description used in logging
    """
    def decorator(func: Callable[[List[Node]], bool]) -> Type[SimulationTestCase]:
        nonlocal name
        if name is None:
            name = func.__name__

        class TestCase(SimulationTestCase):
            def test_iteration(self, nodes: List[Node], iteration: int, timestamp: float):
                if not func(nodes):
                    description_string = "(" + description + ") " if description != "" else ""
                    raise FailedAssertionException(f"Assertion \"{name}\" {description_string}failed\n"
                                                   f"[iteration={iteration} | timestamp={timestamp}]\n")

            def finalize(self):
                pass

        return TestCase

    return decorator


def assert_eventually_true_for_simulation(name: str,
                                          description: str = "") -> Callable[[], Type[SimulationTestCase]]:
    """
    Creates a decorator that will wrap any function receiving all Nodes and returning a boolean into a
    assertion. If at any point in the simulation this function returns True, the assertion succeeds.

    The assertion function should recieve a Node list and return True if the assertion is succesfull 
    and False otherwise.

    Function should be of type `Callable[[List[Node]], bool]`.

    Args:
        name: Name of the assertion, used to identify the assertion
        description: Optional description used in logging
    """
    def decorator(func: Callable[[List[Node]], bool]) -> Type[SimulationTestCase]:
        nonlocal name
        if name is None:
            name = func.__name__

        class TestCase(SimulationTestCase):
            has_been_true = False

            def test_iteration(self, nodes: List[Node], iteration: int, timestamp: float):
                if func(nodes):
                    self.has_been_true = True

            def finalize(self):
                if not self.has_been_true:
                    description_string = "(" + description + ") " if description != "" else ""
                    raise FailedAssertionException(f"Assertion \"{name}\" {description_string}failed\n"
                                                   f"The condition was never met during the simulation")

        return TestCase

    return decorator


class AssertionHandler(INodeHandler):
    """
    Adds assertions to the simulation. Enables users to verify that certain conditions in their simulations 
    are met. Assertions work differently depending on the assertion decorator used, but in general they use
    functions returning a boolean that get called by this handler and raise exceptions when they fail.

    Providers don't interact with this handler. It only consults the simulation status to validate the 
    registered assertions.
    """
    _event_loop: EventLoop
    _nodes: List[Node]

    def __init__(self, assertions: List[Type[SimulationTestCase]]):
        """
        Constructs an assertion handler. The list of decorated assertions is received by parameter and will
        be managed during the simulation.

        Args:
            assertions: List of decorated assertions
        """
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
