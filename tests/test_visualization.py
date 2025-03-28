import unittest

from gradysim.protocol.interface import IProtocol
from gradysim.protocol.messages.telemetry import Telemetry
from gradysim.simulator.extension.visualization_controller import VisualizationController
from gradysim.simulator.handler.visualization import VisualizationHandler
from gradysim.simulator.simulation import SimulationBuilder


class TestVisualization(unittest.TestCase):
    def test_visualization_controller(self):
        dummy_handler = VisualizationHandler()

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

        controller = VisualizationController(simulation.get_node(protocol_id).protocol_encapsulator.protocol)

        controller.paint_node(0, (0, 0, 0))
        controller.resize_nodes(10)
        controller.paint_environment((0, 0, 0))

        self.assertEqual(dummy_handler.command_queue.qsize(), 3)

        paint_command = dummy_handler.command_queue.get()
        self.assertEqual(paint_command['command'], "paint_node")
        self.assertEqual(paint_command['payload']['node_id'], 0)
        self.assertEqual(paint_command['payload']['color'], (0, 0, 0))

        resize_command = dummy_handler.command_queue.get()
        self.assertEqual(resize_command['command'], "resize_nodes")
        self.assertEqual(resize_command['payload']['size'], 10)

        paint_environment_command = dummy_handler.command_queue.get()
        self.assertEqual(paint_environment_command['command'], "paint_environment")
        self.assertEqual(paint_environment_command['payload']['color'], (0, 0, 0))

        self.assertTrue(dummy_handler.command_queue.empty())