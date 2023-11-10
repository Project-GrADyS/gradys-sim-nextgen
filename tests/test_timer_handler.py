import unittest

from gradysim.simulator.event import EventLoop
from gradysim.simulator.handler.timer import TimerHandler, TimerException
from gradysim.simulator.node import Node


def create_timer_handler():
    event_loop = EventLoop()
    timer_handler = TimerHandler()
    timer_handler.inject(event_loop)
    return event_loop, timer_handler


class TestTimerHandler(unittest.TestCase):
    def test_set_timer(self):
        event_loop, timer_handler = create_timer_handler()

        received = 0
        message = ""

        class DummyEncapsulator:
            def handle_timer(self, msg: str):
                nonlocal received, message
                received += 1
                message = msg

        node = Node()
        node.id = 0
        node.protocol_encapsulator = DummyEncapsulator()

        timer_handler.register_node(node)
        timer_handler.set_timer("test", 10, node)

        self.assertEqual(len(event_loop), 1)

        event = event_loop.pop_event()
        self.assertEqual(event.timestamp, 10)
        event.callback()
        self.assertEqual(received, 1)
        self.assertEqual(message, "test")

    def test_set_unregistered(self):
        event_loop, timer_handler = create_timer_handler()

        node = Node()
        node.id = 0

        with self.assertRaises(TimerException):
            timer_handler.set_timer("", 10, node)

    def test_set_in_past(self):
        event_loop, timer_handler = create_timer_handler()

        received = 0
        message = ""

        class DummyEncapsulator:
            def handle_timer(self, msg: str):
                nonlocal received, message
                received += 1
                message = msg

        node = Node()
        node.id = 0
        node.protocol_encapsulator = DummyEncapsulator()

        timer_handler.register_node(node)
        with self.assertRaises(TimerException):
            timer_handler.set_timer("test", -1, node)