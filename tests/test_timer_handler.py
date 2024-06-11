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

    def test_cancel_timer(self):
        event_loop, timer_handler = create_timer_handler()

        received = 0

        class DummyEncapsulator:
            def handle_timer(self, _msg: str):
                nonlocal received
                received += 1

        node = Node()
        node.id = 0
        node.protocol_encapsulator = DummyEncapsulator()

        timer_handler.register_node(node)
        timer_handler.set_timer("test", 10, node)
        timer_handler.cancel_timer("test", node)

        self.assertEqual(len(event_loop), 1)

        # Event still fires, but should not be handled
        event = event_loop.pop_event()
        self.assertEqual(event.timestamp, 10)
        event.callback()
        self.assertEqual(received, 0)


    def test_cancel_non_existing_timer(self):
        event_loop, timer_handler = create_timer_handler()

        node = Node()
        node.id = 0

        with self.assertRaises(TimerException):
            timer_handler.cancel_timer("test", node)

    def test_cancel_two_timers(self):
        event_loop, timer_handler = create_timer_handler()

        received = 0

        class DummyEncapsulator:
            def handle_timer(self, _msg: str):
                nonlocal received
                received += 1

        node = Node()
        node.id = 0
        node.protocol_encapsulator = DummyEncapsulator()

        timer_handler.register_node(node)
        timer_handler.set_timer("test", 10, node)
        timer_handler.set_timer("test", 20, node)
        timer_handler.cancel_timer("test", node)

        self.assertEqual(len(event_loop), 2)

        # Event still fires, but should not be handled
        event = event_loop.pop_event()
        self.assertEqual(event.timestamp, 10)
        event.callback()
        self.assertEqual(received, 0)

        event = event_loop.pop_event()
        self.assertEqual(event.timestamp, 20)
        event.callback()
        self.assertEqual(received, 0)

    def test_schedule_after_cancel(self):
        event_loop, timer_handler = create_timer_handler()

        received = 0

        class DummyEncapsulator:
            def handle_timer(self, _msg: str):
                nonlocal received
                received += 1

        node = Node()
        node.id = 0
        node.protocol_encapsulator = DummyEncapsulator()

        timer_handler.register_node(node)
        timer_handler.set_timer("test", 10, node)
        timer_handler.cancel_timer("test", node)
        timer_handler.set_timer("test", 20, node)

        self.assertEqual(len(event_loop), 2)

        # Event still fires, but should not be handled
        event = event_loop.pop_event()
        self.assertEqual(event.timestamp, 10)
        event.callback()
        self.assertEqual(received, 0)

        event = event_loop.pop_event()
        self.assertEqual(event.timestamp, 20)
        event.callback()
        self.assertEqual(received, 1)

    def cancel_one_node_doesnt_affect_another(self):
        event_loop, timer_handler = create_timer_handler()

        received = 0

        class DummyEncapsulator:
            def handle_timer(self, _msg: str):
                nonlocal received
                received += 1

        node1 = Node()
        node1.id = 0
        node1.protocol_encapsulator = DummyEncapsulator()

        node2 = Node()
        node2.id = 1
        node2.protocol_encapsulator = DummyEncapsulator()

        timer_handler.register_node(node1)
        timer_handler.register_node(node2)
        timer_handler.set_timer("test", 10, node1)
        timer_handler.set_timer("test", 20, node2)
        timer_handler.cancel_timer("test", node1)

        self.assertEqual(len(event_loop), 2)

        # Event still fires, but should not be handled
        event = event_loop.pop_event()
        self.assertEqual(event.timestamp, 10)
        event.callback()
        self.assertEqual(received, 0)

        event = event_loop.pop_event()
        self.assertEqual(event.timestamp, 20)
        event.callback()
        self.assertEqual(received, 1)