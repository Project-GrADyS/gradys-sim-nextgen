import unittest

from gradysim.protocol.interface import IProtocol
from gradysim.protocol.messages.telemetry import Telemetry
from gradysim.protocol.position import Position
from gradysim.simulator.extension.camera import CameraHardware, CameraConfiguration
from gradysim.simulator.handler.mobility import MobilityHandler
from gradysim.simulator.node import Node
from gradysim.simulator.simulation import SimulationBuilder


class TestCameraHardware(unittest.TestCase):
    def build_simulation_with_node_in_position(self, node_position: Position) -> Node:
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
        node_id = builder.add_node(DummyProtocol, (0,0,0))
        builder.add_node(DummyProtocol, node_position)
        builder.add_handler(MobilityHandler())
        simulation = builder.build()
        # Initialize simulation
        simulation.step_simulation()

        return simulation.get_node(node_id)

    def test_detects_nodes_within_reach(self):
        node = self.build_simulation_with_node_in_position((0, 0, -5))

        camera_configuration = CameraConfiguration(camera_reach=10, camera_theta=90, facing_elevation=180, facing_rotation=0)
        camera_hardware = CameraHardware(node.protocol_encapsulator.protocol, camera_configuration)

        detected_nodes = camera_hardware.take_picture()
        self.assertEqual(len(detected_nodes), 1)

    def test_does_not_detect_nodes_out_of_reach(self):
        node = self.build_simulation_with_node_in_position((0, 0, -15))

        camera_configuration = CameraConfiguration(camera_reach=10, camera_theta=90, facing_elevation=0, facing_rotation=0)
        camera_hardware = CameraHardware(node.protocol_encapsulator.protocol, camera_configuration)

        detected_nodes = camera_hardware.take_picture()
        self.assertEqual(len(detected_nodes), 0)

    def test_detects_node_within_angle(self):
        node = self.build_simulation_with_node_in_position((10, 0, 0))

        camera_configuration = CameraConfiguration(camera_reach=10, camera_theta=90, facing_elevation=0, facing_rotation=0)
        camera_hardware = CameraHardware(node.protocol_encapsulator.protocol, camera_configuration)

        detected_nodes = camera_hardware.take_picture()
        self.assertEqual(len(detected_nodes), 1)

    def test_does_not_detect_node_out_of_angle(self):
        node = self.build_simulation_with_node_in_position((10, 0, 0))

        camera_configuration = CameraConfiguration(camera_reach=10, camera_theta=45, facing_elevation=0, facing_rotation=0)
        camera_hardware = CameraHardware(node.protocol_encapsulator.protocol, camera_configuration)

        detected_nodes = camera_hardware.take_picture()
        self.assertEqual(len(detected_nodes), 0)

    def detection_at_position(self, node_position: Position, expected: bool):
        node = self.build_simulation_with_node_in_position(node_position)

        # Camera pointing forward and detecting within 10 units
        camera_configuration = CameraConfiguration(camera_reach=10, camera_theta=90, facing_elevation=90, facing_rotation=0)
        camera_hardware = CameraHardware(node.protocol_encapsulator.protocol, camera_configuration)

        detected_nodes = camera_hardware.take_picture()
        self.assertEqual(len(detected_nodes) > 0, expected)

    def test_detection_at_positions(self):
        self.detection_at_position((0, 0, 0), True),  # Node at same position
        self.detection_at_position((10, 0, 0), True),  # Node in front within range
        self.detection_at_position((11, 0, 0), False),  # Node in front out of range
        self.detection_at_position((0, 10, 0), True), # Node to the right within range
        self.detection_at_position((0, 11, 0), False), # Node to the right out of range
        self.detection_at_position((0, -10, 0), True), # Node to the left within range
        self.detection_at_position((0, -11, 0), False), # Node to the left out of range
        self.detection_at_position((0, 0, 10), True), # Node above within range
        self.detection_at_position((0, 0, 11), False), # Node above out of range
        self.detection_at_position((0, 0, -10), True), # Node below within range
        self.detection_at_position((0, 0, -11), False), # Node below out of range
        self.detection_at_position((-1, 0, 0), False),  # Node behind