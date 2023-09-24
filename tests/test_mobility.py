import math
import unittest

from simulator.event import EventLoop
from simulator.messages.mobility import MobilityCommand, MobilityCommandType
from simulator.node import Node
from simulator.node.handler.mobility import MobilityHandler, MobilitySettings, MobilityException


def setup_mobility_handler(settings: MobilitySettings):
    mobility_handler = MobilityHandler(settings)
    event_loop = EventLoop()
    mobility_handler.inject(event_loop)
    return event_loop, mobility_handler


class TestMobility(unittest.TestCase):
    def test_default_speed(self):
        node = Node()
        node.id = 0
        node.position = (0, 0, 0)

        speed = 1.2
        update_rate = 0.3

        event_loop, mobility_handler = setup_mobility_handler(MobilitySettings(update_rate=update_rate,
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

        update_rate = 0.3
        event_loop, mobility_handler = setup_mobility_handler(MobilitySettings(update_rate=update_rate))
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
        event_loop, mobility_handler = setup_mobility_handler(MobilitySettings(update_rate=update_rate))

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

        update_rate = 0.3
        speed = 1
        event_loop, mobility_handler = setup_mobility_handler(MobilitySettings(update_rate=update_rate,
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

        update_rate = 1
        speed = 100
        event_loop, mobility_handler = setup_mobility_handler(MobilitySettings(update_rate=update_rate,
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

    def test_register_not_injected(self):
        mobility_handler = MobilityHandler(MobilitySettings())

        node = Node()
        node.id = 0

        with self.assertRaises(MobilityException):
            mobility_handler.register_node(node)

    def test_command_not_registered(self):
        mobility_handler = MobilityHandler(MobilitySettings())
        node = Node()
        node.id = 0

        with self.assertRaises(MobilityException):
            mobility_handler.handle_command(MobilityCommand(MobilityCommandType.SET_SPEED), node)
