import unittest
from typing import List

from gradys.protocol.interface import IProtocol
from gradys.protocol.messages.telemetry import Telemetry
from gradys.simulator.handler.assertion import AssertionHandler, assert_always_true_for_simulation, \
    FailedAssertionException, assert_always_true_for_protocol
from gradys.simulator.handler.mobility import MobilityHandler
from gradys.simulator.node import Node
from gradys.simulator.simulation import SimulationBuilder, SimulationConfiguration


class TestAssertionHandler(unittest.TestCase):
    def test_always_assertion_succesful(self):
        builder = SimulationBuilder(SimulationConfiguration(max_iterations=2))

        @assert_always_true_for_simulation("always true")
        def assert_number_of_nodes(nodes: List[Node]):
            return len(nodes) == 0

        builder.add_handler(AssertionHandler([assert_number_of_nodes]))
        builder.add_handler(MobilityHandler())
        builder.build().start_simulation()
        self.assertTrue(True)

    def test_always_assertion_failure(self):
        builder = SimulationBuilder(SimulationConfiguration(max_iterations=2))

        @assert_always_true_for_simulation("always false")
        def assert_number_of_nodes(nodes: List[Node]):
            return len(nodes) == 0

        class DummyProtocol(IProtocol):

            def initialize(self, stage: int):
                pass

            def handle_timer(self, timer: str):
                pass

            def handle_packet(self, message: str):
                pass

            def handle_telemetry(self, telemetry: Telemetry):
                pass

            def finish(self):
                pass

        builder.add_handler(AssertionHandler([assert_number_of_nodes]))
        builder.add_handler(MobilityHandler())
        builder.add_node(DummyProtocol, (0, 0, 0))
        with self.assertRaises(FailedAssertionException):
            builder.build().start_simulation()

    def verify_protocol_always_assertion(self, success: bool):
        builder = SimulationBuilder(SimulationConfiguration(max_iterations=1))

        class DummyProtocol(IProtocol):
            variable = True

            def initialize(self, stage: int):
                pass

            def handle_timer(self, timer: str):
                pass

            def handle_packet(self, message: str):
                pass

            def handle_telemetry(self, telemetry: Telemetry):
                pass

            def finish(self):
                pass

        @assert_always_true_for_protocol(DummyProtocol, "always true")
        def assert_number_of_nodes(node: Node[DummyProtocol]):
            return node.protocol_encapsulator.protocol.variable \
                if success else not node.protocol_encapsulator.protocol.variable

        builder.add_handler(AssertionHandler([assert_number_of_nodes]))
        builder.add_handler(MobilityHandler())
        builder.add_node(DummyProtocol, (0, 0, 0))
        builder.build().start_simulation()
        self.assertTrue(True)

    def test_protocol_always_assertion_success(self):
        self.verify_protocol_always_assertion(True)

    def test_protocol_always_assertion_failure(self):
        with self.assertRaises(FailedAssertionException):
            self.verify_protocol_always_assertion(False)
