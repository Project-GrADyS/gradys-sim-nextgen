import unittest

from gradysim.protocol.addons.follow_mobility import MobilityLeaderAddon, MobilityFollowerAddon
from gradysim.protocol.interface import IProtocol
from gradysim.protocol.messages.mobility import GotoCoordsMobilityCommand, SetSpeedMobilityCommand
from gradysim.protocol.messages.telemetry import Telemetry
from gradysim.simulator.handler.assertion import assert_eventually_true_for_protocol, AssertionHandler
from gradysim.simulator.handler.communication import CommunicationHandler
from gradysim.simulator.handler.mobility import MobilityHandler
from gradysim.simulator.handler.timer import TimerHandler
from gradysim.simulator.node import Node
from gradysim.simulator.simulation import SimulationBuilder, SimulationConfiguration, PositionScheme


class DummyLeaderProtocol(IProtocol):
    leader: MobilityLeaderAddon

    def initialize(self, stage: int) -> None:
        self.leader = MobilityLeaderAddon(self)

        # Setting target far away and speed high
        destination_command = GotoCoordsMobilityCommand(100, 100, 100)
        self.provider.send_mobility_command(destination_command)

        speed_command = SetSpeedMobilityCommand(1)
        self.provider.send_mobility_command(speed_command)

    def handle_timer(self, timer: str) -> None:
        pass

    def handle_packet(self, message: str) -> None:
        pass

    def handle_telemetry(self, telemetry: Telemetry) -> None:
        pass

    def finish(self) -> None:
        pass


class DummyFollowProtocol(IProtocol):
    follower: MobilityFollowerAddon

    def initialize(self, stage: int) -> None:
        self.follower = MobilityFollowerAddon(self)

        # Setting speed lower than leader
        speed_command = SetSpeedMobilityCommand(0.1)
        self.provider.send_mobility_command(speed_command)

    def handle_timer(self, timer: str) -> None:
        pass

    def handle_packet(self, message: str) -> None:
        pass

    def handle_telemetry(self, telemetry: Telemetry) -> None:
        pass

    def finish(self) -> None:
        pass


@assert_eventually_true_for_protocol(DummyLeaderProtocol, "assert_that_all_followed")
def assert_that_all_followed(node: Node[DummyLeaderProtocol]):
    return len(node.protocol_encapsulator.protocol.leader.followers) == 10


@assert_eventually_true_for_protocol(DummyFollowProtocol, "assert_that_all_had_leader")
def assert_that_all_had_leader(node: Node[DummyFollowProtocol]):
    follower = node.protocol_encapsulator.protocol.follower
    return (follower.current_leader is not None
            and len(follower.available_leaders) == 1
            and follower.current_leader_position is not None)


@assert_eventually_true_for_protocol(DummyLeaderProtocol, "assert_that_eventually_no_followers")
def assert_that_eventually_no_followers(node: Node[DummyLeaderProtocol]):
    return len(node.protocol_encapsulator.protocol.leader.followers) == 0


@assert_eventually_true_for_protocol(DummyFollowProtocol, "assert_that_eventually_no_leader")
def assert_that_eventually_no_leader(node: Node[DummyFollowProtocol]):
    follower = node.protocol_encapsulator.protocol.follower
    return (follower.current_leader is None
            and len(follower.available_leaders) == 0
            and follower.current_leader_position is None)


class FollowMobilityTestCase(unittest.TestCase):
    def test_follow_mobility(self):
        # Setting up simulation
        config = SimulationConfiguration(
            duration=100
        )

        builder = SimulationBuilder(config)

        # Adding leader
        builder.add_node(DummyLeaderProtocol, (0, 0, 0))

        # Adding followers
        for _ in range(10):
            builder.add_node(DummyFollowProtocol,
                             PositionScheme.random((-5, 5), (-5, 5), (0, 5)))

        # Setting up handlers
        builder.add_handler(MobilityHandler())
        builder.add_handler(TimerHandler())
        builder.add_handler(CommunicationHandler())

        # Setting up assertions
        assertion_handler = AssertionHandler([assert_that_all_followed,
                                              assert_that_all_had_leader,
                                              assert_that_eventually_no_followers,
                                              assert_that_eventually_no_leader])
        builder.add_handler(assertion_handler)

        simulation = builder.build()

        simulation.start_simulation()
        self.assertTrue(True)
