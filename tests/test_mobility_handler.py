import math
import unittest
from typing import Type

from gradysim.protocol.interface import IProtocol
from gradysim.encapsulator.interface import IEncapsulator
from gradysim.simulator.event import EventLoop
from gradysim.protocol.messages.mobility import MobilityCommand, MobilityCommandType
from gradysim.protocol.messages.telemetry import Telemetry
from gradysim.simulator.handler.mobility import MobilityHandler, MobilityConfiguration, MobilityException
from gradysim.simulator.node import Node
from gradysim.simulator.simulation import SimulationBuilder, SimulationConfiguration


def setup_mobility_handler(settings: MobilityConfiguration):
    mobility_handler = MobilityHandler(settings)
    event_loop = EventLoop()
    mobility_handler.inject(event_loop)
    return event_loop, mobility_handler


class DummyEncapsulator(IEncapsulator):

    def encapsulate(self, protocol: Type[IProtocol]):
        pass

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


class TestMobility(unittest.TestCase):
    def test_default_speed(self):
        node = Node()
        node.id = 0
        node.position = (0, 0, 0)
        node.protocol_encapsulator = DummyEncapsulator()

        speed = 1.2
        update_rate = 0.3

        event_loop, mobility_handler = setup_mobility_handler(MobilityConfiguration(update_rate=update_rate,
                                                                                    default_speed=speed))
        mobility_handler.register_node(node)
        mobility_handler.handle_command(MobilityCommand(
            MobilityCommandType.GOTO_COORDS,
            10,
            0,
            0
        ), node)

        event = event_loop.pop_event()
        event.callback()

        self.assertEqual(node.position, (speed * update_rate, 0, 0))

    def test_set_speed(self):
        node = Node()
        node.id = 0
        node.position = (0, 0, 0)
        node.protocol_encapsulator = DummyEncapsulator()

        update_rate = 0.3
        event_loop, mobility_handler = setup_mobility_handler(MobilityConfiguration(update_rate=update_rate))
        mobility_handler.register_node(node)

        mobility_handler.handle_command(MobilityCommand(
            MobilityCommandType.GOTO_COORDS,
            10,
            0,
            0
        ), node)

        speed = 10
        mobility_handler.handle_command(MobilityCommand(
            MobilityCommandType.SET_SPEED,
            speed
        ), node)
        node.position = (0, 0, 0)

        event = event_loop.pop_event()
        event.callback()

        self.assertEqual(node.position, (speed * update_rate, 0, 0))

    def test_update_rate(self):
        update_rate = 0.1
        event_loop, mobility_handler = setup_mobility_handler(MobilityConfiguration(update_rate=update_rate))

        self.assertEqual(len(event_loop), 1)
        event = event_loop.pop_event()
        event.callback()
        self.assertEqual(event.timestamp, update_rate)
        event = event_loop.pop_event()
        event.callback()
        self.assertEqual(event.timestamp, update_rate * 2)

    def test_movement(self):
        node = Node()
        node.id = 0
        node.position = (0, 0, 0)
        node.protocol_encapsulator = DummyEncapsulator()

        update_rate = 0.3
        speed = 1
        event_loop, mobility_handler = setup_mobility_handler(MobilityConfiguration(update_rate=update_rate,
                                                                                    default_speed=speed))
        mobility_handler.register_node(node)

        mobility_handler.handle_command(MobilityCommand(
            MobilityCommandType.GOTO_COORDS,
            1,
            1,
            1
        ), node)

        event = event_loop.pop_event()
        event.callback()

        self.assertEqual(node.position, (
            speed * update_rate / math.sqrt(3),
            speed * update_rate / math.sqrt(3),
            speed * update_rate / math.sqrt(3)
        ))

    def test_cant_overshoot(self):
        node = Node()
        node.id = 0
        node.position = (0, 0, 0)
        node.protocol_encapsulator = DummyEncapsulator()

        update_rate = 1
        speed = 100
        event_loop, mobility_handler = setup_mobility_handler(MobilityConfiguration(update_rate=update_rate,
                                                                                    default_speed=speed))
        mobility_handler.register_node(node)

        mobility_handler.handle_command(MobilityCommand(
            MobilityCommandType.GOTO_COORDS,
            1,
            1,
            1
        ), node)

        event = event_loop.pop_event()
        event.callback()

        self.assertEqual(node.position, (1, 1, 1))

    def test_telemetry_flow(self):
        received = 0

        class DummyProtocol(IProtocol):
            def initialize(self, stage: int):
                pass

            def handle_timer(self, timer: str):
                pass

            def handle_packet(self, message: str):
                pass

            def finish(self):
                pass

            def handle_telemetry(self, _telemetry):
                nonlocal received
                received += 1

        builder = SimulationBuilder(SimulationConfiguration(max_iterations=5))
        builder.add_node(DummyProtocol, (0, 0, 0))
        builder.add_handler(MobilityHandler())
        simulation = builder.build()

        simulation.start_simulation()

        self.assertEqual(5, received)

    def test_register_not_injected(self):
        mobility_handler = MobilityHandler(MobilityConfiguration())

        node = Node()
        node.id = 0

        with self.assertRaises(MobilityException):
            mobility_handler.register_node(node)

    def test_command_not_registered(self):
        mobility_handler = MobilityHandler(MobilityConfiguration())
        node = Node()
        node.id = 0

        with self.assertRaises(MobilityException):
            mobility_handler.handle_command(MobilityCommand(MobilityCommandType.SET_SPEED), node)
