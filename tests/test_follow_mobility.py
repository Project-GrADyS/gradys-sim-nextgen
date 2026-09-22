import json
import unittest

from gradysim.protocol.plugin.follow_mobility import (
    MobilityLeaderPlugin,
    MobilityLeaderConfiguration,
    MobilityFollowerPlugin,
    MobilityFollowerConfiguration,
)
from gradysim.protocol.plugin.follow_mobility.mobility import (
    LEADER_TAG,
    BROADCAST_TIMER_TAG,
    FOLLOWER_TIMER_TAG,
)
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
    leader: MobilityLeaderPlugin

    def initialize(self) -> None:
        self.leader = MobilityLeaderPlugin(self)

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
    follower: MobilityFollowerPlugin

    def initialize(self) -> None:
        self.follower = MobilityFollowerPlugin(self)

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


class DummyOrientedLeaderProtocol(IProtocol):
    leader: MobilityLeaderPlugin

    def initialize(self) -> None:
        self.leader = MobilityLeaderPlugin(self, MobilityLeaderConfiguration(initial_orientation=90.0))

    def handle_timer(self, timer: str) -> None:
        pass

    def handle_packet(self, message: str) -> None:
        pass

    def handle_telemetry(self, telemetry: Telemetry) -> None:
        pass

    def finish(self) -> None:
        pass


class DummyOrientedFollowProtocol(IProtocol):
    follower: MobilityFollowerPlugin

    def initialize(self) -> None:
        self.follower = MobilityFollowerPlugin(self)
        self.follower.set_relative_position((10, 0, 0))
        speed_command = SetSpeedMobilityCommand(10)
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


@assert_eventually_true_for_protocol(DummyOrientedFollowProtocol, "assert_follower_oriented_position")
def assert_follower_oriented_position(node: Node[DummyOrientedFollowProtocol]):
    follower = node.protocol_encapsulator.protocol.follower
    pos = node.position
    dist_sq = (pos[0] - 0) ** 2 + (pos[1] - 10) ** 2 + (pos[2] - 0) ** 2
    return follower.current_leader_orientation == 90.0 and dist_sq < 0.1


class MockProvider:
    def __init__(self, node_id: int = 1):
        self.node_id = node_id
        self._current_time = 0.0
        self.comm_commands = []
        self.mobility_commands = []
        self.timers = {}

    def get_id(self) -> int:
        return self.node_id

    def current_time(self) -> float:
        return self._current_time

    def send_communication_command(self, command) -> None:
        self.comm_commands.append(command)

    def send_mobility_command(self, command) -> None:
        self.mobility_commands.append(command)

    def schedule_timer(self, timer: str, timestamp: float) -> None:
        self.timers[timer] = timestamp


class MockProtocol(IProtocol):
    def __init__(self, provider: MockProvider):
        self.provider = provider

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

    def test_leader_orientation_broadcast(self):
        provider = MockProvider(node_id=1)
        protocol = MockProtocol(provider)
        leader = MobilityLeaderPlugin(protocol, MobilityLeaderConfiguration(initial_orientation=45.0))
        self.assertEqual(leader.orientation, 45.0)

        leader.set_orientation(90.0)
        self.assertEqual(leader.orientation, 90.0)

        # Trigger broadcast timer
        protocol.handle_timer(BROADCAST_TIMER_TAG)
        self.assertTrue(len(provider.comm_commands) > 0)
        last_comm = provider.comm_commands[-1]
        self.assertTrue(last_comm.message.startswith(LEADER_TAG))
        payload = json.loads(last_comm.message[len(f"{LEADER_TAG}:"):])
        self.assertEqual(payload["orientation"], 90.0)

    def test_follower_orientation_shifts_destination(self):
        provider = MockProvider(node_id=2)
        protocol = MockProtocol(provider)
        follower = MobilityFollowerPlugin(protocol)
        follower.set_relative_position((10.0, 0.0, 5.0))

        # Make follower follow leader 1
        broadcast_msg = f"{LEADER_TAG}:{json.dumps({'id': 1, 'position': [0.0, 0.0, 0.0], 'orientation': 90.0})}"
        protocol.handle_packet(broadcast_msg)
        follower.follow_leader(1)

        # Send broadcast again while following
        provider.mobility_commands.clear()
        protocol.handle_packet(broadcast_msg)

        self.assertEqual(follower.current_leader_orientation, 90.0)
        self.assertTrue(len(provider.mobility_commands) > 0)
        last_mob = provider.mobility_commands[-1]
        # (10, 0, 5) rotated 90 deg CCW is (0, 10, 5)
        self.assertAlmostEqual(last_mob.param_1, 0.0)
        self.assertAlmostEqual(last_mob.param_2, 10.0)
        self.assertEqual(last_mob.param_3, 5.0)

        # Test another orientation (180 deg)
        broadcast_msg_180 = f"{LEADER_TAG}:{json.dumps({'id': 1, 'position': [0.0, 0.0, 0.0], 'orientation': 180.0})}"
        protocol.handle_packet(broadcast_msg_180)
        self.assertEqual(follower.current_leader_orientation, 180.0)
        last_mob = provider.mobility_commands[-1]
        # (10, 0, 5) rotated 180 deg is (-10, 0, 5)
        self.assertAlmostEqual(last_mob.param_1, -10.0)
        self.assertAlmostEqual(last_mob.param_2, 0.0)
        self.assertEqual(last_mob.param_3, 5.0)

    def test_follower_orientation_disabled(self):
        provider = MockProvider(node_id=2)
        protocol = MockProtocol(provider)
        follower = MobilityFollowerPlugin(protocol, MobilityFollowerConfiguration(follow_orientation=False))
        follower.set_relative_position((10.0, 0.0, 5.0))

        broadcast_msg = f"{LEADER_TAG}:{json.dumps({'id': 1, 'position': [0.0, 0.0, 0.0], 'orientation': 90.0})}"
        protocol.handle_packet(broadcast_msg)
        follower.follow_leader(1)

        provider.mobility_commands.clear()
        protocol.handle_packet(broadcast_msg)

        self.assertEqual(follower.current_leader_orientation, 90.0)
        self.assertTrue(len(provider.mobility_commands) > 0)
        last_mob = provider.mobility_commands[-1]
        # Should NOT be rotated because follow_orientation is False
        self.assertEqual(last_mob.param_1, 10.0)
        self.assertEqual(last_mob.param_2, 0.0)
        self.assertEqual(last_mob.param_3, 5.0)

    def test_follower_orientation_reset_on_timeout(self):
        provider = MockProvider(node_id=2)
        protocol = MockProtocol(provider)
        follower = MobilityFollowerPlugin(protocol, MobilityFollowerConfiguration(leader_timeout=1.0))

        broadcast_msg = f"{LEADER_TAG}:{json.dumps({'id': 1, 'position': [0.0, 0.0, 0.0], 'orientation': 90.0})}"
        protocol.handle_packet(broadcast_msg)
        follower.follow_leader(1)
        protocol.handle_packet(broadcast_msg)
        self.assertEqual(follower.current_leader_orientation, 90.0)

        # Advance time past timeout
        provider._current_time = 5.0
        protocol.handle_timer(FOLLOWER_TIMER_TAG)
        self.assertIsNone(follower.current_leader)
        self.assertIsNone(follower.current_leader_orientation)

    def test_follow_mobility_with_orientation_simulation(self):
        config = SimulationConfiguration(duration=10)
        builder = SimulationBuilder(config)

        builder.add_node(DummyOrientedLeaderProtocol, (0, 0, 0))
        builder.add_node(DummyOrientedFollowProtocol, (0, 0, 0))

        builder.add_handler(MobilityHandler())
        builder.add_handler(TimerHandler())
        builder.add_handler(CommunicationHandler())

        assertion_handler = AssertionHandler([assert_follower_oriented_position])
        builder.add_handler(assertion_handler)

        simulation = builder.build()
        simulation.start_simulation()
        self.assertTrue(True)

