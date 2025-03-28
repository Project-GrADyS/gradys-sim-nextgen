import unittest

from gradysim.protocol.interface import IProtocol
from gradysim.protocol.messages.telemetry import Telemetry
from gradysim.simulator.extension.communication_controller import CommunicationController
from gradysim.simulator.handler.communication import CommunicationHandler
from gradysim.simulator.simulation import SimulationBuilder


class TestVisualization(unittest.TestCase):
    def test_communication_controller(self):
        dummy_handler = CommunicationHandler()

        class DummyProtocol(IProtocol):
            def initialize(self) -> None:
                pass

            def handle_timer(self, timer: str) -> None:
                pass

            def handle_packet(self, message: str) -> None:
                pass

            def handle_telemetry(self, telemetry: Telemetry) -> None:
                pass

            def finish(self) -> None:
                pass

        builder = SimulationBuilder()
        builder.add_handler(dummy_handler)
        protocol_id = builder.add_node(DummyProtocol, (0, 0, 0))
        simulation = builder.build()

        controller = CommunicationController(simulation.get_node(protocol_id).protocol_encapsulator.protocol)
        controller.set_transmission_range(99)

        self.assertEqual(dummy_handler.transmission_ranges[protocol_id], 99)

    def test_communication_controller_no_handler(self):
        class DummyProtocol(IProtocol):
            def initialize(self) -> None:
                pass

            def handle_timer(self, timer: str) -> None:
                pass

            def handle_packet(self, message: str) -> None:
                pass

            def handle_telemetry(self, telemetry: Telemetry) -> None:
                pass

            def finish(self) -> None:
                pass

        builder = SimulationBuilder()
        protocol_id = builder.add_node(DummyProtocol, (0, 0, 0))
        simulation = builder.build()

        controller = CommunicationController(simulation.get_node(protocol_id).protocol_encapsulator.protocol)

        with self.assertLogs() as cm:
            controller.set_transmission_range(99)
            self.assertIn("No communication handler detected, command ignored.", cm.output[0])