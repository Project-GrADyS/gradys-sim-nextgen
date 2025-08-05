import unittest

from gradysim.protocol.messages.telemetry import Telemetry
from gradysim.protocol.plugin.radio import Radio, RadioConfiguration
from gradysim.protocol.messages.communication import CommunicationCommand, CommunicationCommandType
from gradysim.simulator.handler.communication import CommunicationHandler
from gradysim.simulator.simulation import SimulationBuilder, SimulationConfiguration
from gradysim.protocol.interface import IProtocol
from gradysim.protocol.position import Position

# Factory function to generate protocol classes with custom radio config

def make_test_protocol(radio_range=0, radio2_range=0):
    class TestProtocol(IProtocol):
        def handle_timer(self, timer: str) -> None:
            pass
        def handle_telemetry(self, telemetry: Telemetry) -> None:
            pass
        def finish(self) -> None:
            pass
        def __init__(self):
            self.received_messages = []
            self.radio_range = radio_range
            self.radio2_range = radio2_range
            self.radio = None
            self.radio2 = None
            self.provider = None

        def initialize(self):
            self.radio = Radio(self, RadioConfiguration(range=self.radio_range))
            self.radio2 = Radio(self, RadioConfiguration(range=self.radio2_range))

        def handle_packet(self, message: str):
            self.received_messages.append(message)
        def send(self, message, destination=None, use_radio=False, use_radio2=False):
            command = CommunicationCommand(
                command_type=CommunicationCommandType.SEND,
                message=message,
                destination=destination
            )
            if use_radio2:
                self.radio2.send_communication_command(command)
            elif use_radio:
                self.radio.send_communication_command(command)
            else:
                self.provider.send_communication_command(command)
    return TestProtocol

class TestRadioPlugin(unittest.TestCase):
    def setUp(self):
        self.config = SimulationConfiguration(duration=1)

    def _run_sim(self, protocol_classes, positions):
        builder = SimulationBuilder(self.config)
        node_ids = []
        for proto_cls, pos in zip(protocol_classes, positions):
            node_id = builder.add_node(proto_cls, pos)
            node_ids.append(node_id)

        builder.add_handler(CommunicationHandler())
        sim = builder.build()
        return sim, node_ids

    def test_radio_respects_range(self):
        # Node 0 uses radio with range 10, node 1 is in range, node 2 is out of range
        Proto0 = make_test_protocol(radio_range=10)
        Proto1 = make_test_protocol()
        Proto2 = make_test_protocol()
        sim, node_ids = self._run_sim([Proto0, Proto1, Proto2], [(0,0,0), (5,0,0), (20,0,0)])
        proto0 = sim.get_node(node_ids[0]).protocol_encapsulator.protocol
        proto1 = sim.get_node(node_ids[1]).protocol_encapsulator.protocol
        proto2 = sim.get_node(node_ids[2]).protocol_encapsulator.protocol
        sim._initialize_simulation()
        proto0.send("hello", destination=1, use_radio=True)
        proto0.send("world", destination=2, use_radio=True)
        sim.start_simulation()
        self.assertIn("hello", proto1.received_messages)
        self.assertNotIn("world", proto2.received_messages)

    def test_provider_not_affected_by_radio(self):
        # Node 0 uses radio with range 10, but sends via provider. Should ignore radio range and use default range
        # of 60
        Proto0 = make_test_protocol(radio_range=10)
        Proto1 = make_test_protocol()
        sim, node_ids = self._run_sim([Proto0, Proto1], [(0,0,0), (50,0,0)])
        proto0 = sim.get_node(node_ids[0]).protocol_encapsulator.protocol
        proto1 = sim.get_node(node_ids[1]).protocol_encapsulator.protocol
        sim._initialize_simulation()
        proto0.send("direct", destination=1, use_radio=False)
        sim.start_simulation()
        self.assertIn("direct", proto1.received_messages)

    def test_multiple_radios_independent(self):
        # Node 0 has two radios with different ranges
        Proto0 = make_test_protocol(radio_range=10, radio2_range=100)
        Proto1 = make_test_protocol()
        Proto2 = make_test_protocol()
        sim, node_ids = self._run_sim([Proto0, Proto1, Proto2], [(0,0,0), (5,0,0), (50,0,0)])
        proto0 = sim.get_node(node_ids[0]).protocol_encapsulator.protocol
        proto1 = sim.get_node(node_ids[1]).protocol_encapsulator.protocol
        proto2 = sim.get_node(node_ids[2]).protocol_encapsulator.protocol
        sim._initialize_simulation()
        proto0.send("short", destination=1, use_radio=True)
        proto0.send("long", destination=2, use_radio2=True)
        sim.start_simulation()
        self.assertIn("short", proto1.received_messages)
        self.assertIn("long", proto2.received_messages)
        # Node 2 should not receive the short-range message
        self.assertNotIn("short", proto2.received_messages)

if __name__ == "__main__":
    unittest.main()
