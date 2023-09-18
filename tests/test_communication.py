import unittest

from simulator.messages.communication import CommunicationCommand, CommunicationCommandType
from simulator.node import Node
from simulator.node.communication import Medium, can_transmit, CommunicationHandler, CommunicationException


class TestCommunication(unittest.TestCase):
    def test_transmission_range(self):
        medium: Medium = {
            "transmission_range": 10
        }

        self.assertTrue(can_transmit((0, 0, 0), (10, 0, 0), medium))
        self.assertTrue(can_transmit((0, 0, 0), (0, 0, 0), medium))
        self.assertTrue(can_transmit((0, 0, 0), (-3, -3, 0), medium))

        self.assertFalse(can_transmit((0, 0, 0), (10.001, 0, 0), medium))
        self.assertFalse(can_transmit((10, 0, 0), (-10, 0, 0), medium))
        self.assertFalse(can_transmit((0, 0, 0), (30, 0, 0), medium))
        self.assertFalse(can_transmit((0, 0, 0), (8, 8, 8), medium))

    def handle_command_helper(self, command: CommunicationCommand):
        medium: Medium = {
            "transmission_range": 10
        }

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

        comm_handler.register_node(node1)
        comm_handler.register_node(node2)

        # Testing successful command
        comm_handler.handle_command(command, node1)

        return received

    def test_successful_send_command(self):
        command = CommunicationCommand(
            CommunicationCommandType.SEND,
            {},
            2
        )
        received = self.handle_command_helper(command)
        self.assertEqual(received, 1)

    def test_successful_broadcast_command(self):
        command = CommunicationCommand(
            CommunicationCommandType.BROADCAST,
            {}
        )
        received = self.handle_command_helper(command)
        self.assertEqual(received, 1)

    def test_failure_no_destination_send(self):
        command = CommunicationCommand(
            CommunicationCommandType.SEND,
            {}
        )
        self.assertRaises(CommunicationException, self.handle_command_helper, command)

    def test_failure_self_message(self):
        command = CommunicationCommand(
            CommunicationCommandType.SEND,
            {},
            1
        )
        self.assertRaises(CommunicationException, self.handle_command_helper, command)

    def test_failure_non_existing_target(self):
        command = CommunicationCommand(
            CommunicationCommandType.SEND,
            {},
            10
        )
        self.assertRaises(CommunicationException, self.handle_command_helper, command)
