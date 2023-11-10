import unittest

from gradysim.simulator.event import EventLoop
from gradysim.protocol.messages.communication import CommunicationCommand, CommunicationCommandType
from gradysim.simulator.node import Node
from gradysim.simulator.handler.communication import CommunicationMedium, can_transmit, CommunicationHandler, \
    CommunicationException


def handle_command_helper(command: CommunicationCommand):
    medium = CommunicationMedium(transmission_range=10)

    received = 0

    class DummyEncapsulator:
        def handle_packet(self, _message: dict):
            nonlocal received
            received += 1

    node1 = Node()
    node1.id = 1
    node1.position = (0, 0, 0)
    node1.protocol_encapsulator = DummyEncapsulator()

    node2 = Node()
    node2.id = 2
    node2.position = (5, 5, 5)
    node2.protocol_encapsulator = DummyEncapsulator()

    comm_handler = CommunicationHandler(medium)
    event_loop = EventLoop()
    comm_handler.inject(event_loop)

    comm_handler.register_node(node1)
    comm_handler.register_node(node2)

    # Testing successful command
    comm_handler.handle_command(command, node1)

    event_loop.pop_event().callback()
    return received


class TestCommunication(unittest.TestCase):
    def test_transmission_range(self):
        medium = CommunicationMedium(transmission_range=10)

        self.assertTrue(can_transmit((0, 0, 0), (10, 0, 0), medium))
        self.assertTrue(can_transmit((0, 0, 0), (0, 0, 0), medium))
        self.assertTrue(can_transmit((0, 0, 0), (-3, -3, 0), medium))

        self.assertFalse(can_transmit((0, 0, 0), (10.001, 0, 0), medium))
        self.assertFalse(can_transmit((10, 0, 0), (-10, 0, 0), medium))
        self.assertFalse(can_transmit((0, 0, 0), (30, 0, 0), medium))
        self.assertFalse(can_transmit((0, 0, 0), (8, 8, 8), medium))

    def test_successful_send_command(self):
        command = CommunicationCommand(
            CommunicationCommandType.SEND,
            "",
            2
        )
        received = handle_command_helper(command)
        self.assertEqual(received, 1)

    def test_successful_broadcast_command(self):
        command = CommunicationCommand(
            CommunicationCommandType.BROADCAST,
            ""
        )
        received = handle_command_helper(command)
        self.assertEqual(received, 1)

    def test_failure_no_destination_send(self):
        command = CommunicationCommand(
            CommunicationCommandType.SEND,
            ""
        )
        self.assertRaises(CommunicationException, handle_command_helper, command)

    def test_failure_self_message(self):
        command = CommunicationCommand(
            CommunicationCommandType.SEND,
            "",
            1
        )
        self.assertRaises(CommunicationException, handle_command_helper, command)

    def test_failure_non_existing_target(self):
        command = CommunicationCommand(
            CommunicationCommandType.SEND,
            "",
            10
        )
        self.assertRaises(CommunicationException, handle_command_helper, command)

    def test_register_not_injected(self):
        node1 = Node()
        node1.id = 1
        node1.position = (0, 0, 0)

        medium = CommunicationMedium()
        comm_handler = CommunicationHandler(medium)

        with self.assertRaises(CommunicationException):
            comm_handler.register_node(node1)

    def test_delay(self):
        # Setting up nodes
        received = 0
        class DummyEncapsulator:
            def handle_packet(self, _message: dict):
                nonlocal received
                received += 1

        node1 = Node()
        node1.id = 1
        node1.position = (0, 0, 0)
        node1.protocol_encapsulator = DummyEncapsulator()

        node2 = Node()
        node2.id = 2
        node2.position = (5, 5, 5)
        node2.protocol_encapsulator = DummyEncapsulator()

        # Setting up comm_handler
        delay = 1
        medium = CommunicationMedium(delay=delay)
        event_loop = EventLoop()
        comm_handler = CommunicationHandler(medium)
        comm_handler.inject(event_loop)

        comm_handler.register_node(node1)
        comm_handler.register_node(node2)

        # Sending message
        command = CommunicationCommand(
            CommunicationCommandType.SEND,
            "",
            2
        )
        comm_handler.handle_command(command, node1)

        # Assert that event has been queued
        self.assertEqual(len(event_loop), 1)

        # Assert that timestamp is consistent with delay
        current_time = event_loop.current_time
        event = event_loop.pop_event()
        self.assertEqual(event.timestamp, current_time + delay)

        # Assert that message is received
        event.callback()
        self.assertEqual(received, 1)

    def test_failure(self):
        medium = CommunicationMedium(failure_rate=0)
        self.assertTrue(can_transmit((0, 0, 0), (0, 0, 0), medium))

        medium = CommunicationMedium(failure_rate=1)
        self.assertFalse(can_transmit((0, 0, 0), (0, 0, 0), medium))
