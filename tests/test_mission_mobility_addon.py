import unittest
from collections import defaultdict

from gradysim.protocol.plugin.mission_mobility import MissionMobilityPlugin, MissionMobilityConfiguration, LoopMission, \
    MissionMobilityPluginException
from gradysim.protocol.interface import IProtocol, IProvider
from gradysim.protocol.messages.communication import CommunicationCommand
from gradysim.protocol.messages.mobility import MobilityCommand, MobilityCommandType
from gradysim.protocol.messages.telemetry import Telemetry


class TestMissionMobilityPlugin(unittest.TestCase):

    def setUp(self) -> None:
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

        commands_sent = defaultdict(lambda: 0)
        self.commands_sent = commands_sent

        class DummyProvider(IProvider):
            def send_communication_command(self, command: CommunicationCommand) -> None:
                pass

            def send_mobility_command(self, command: MobilityCommand) -> None:
                nonlocal commands_sent
                commands_sent[command.command_type] += 1

            def schedule_timer(self, timer: str, timestamp: float) -> None:
                pass

            def cancel_timer(self, timer: str) -> None:
                pass

            def current_time(self) -> float:
                pass

            def get_id(self) -> int:
                pass

        self.protocol = DummyProtocol()
        self.protocol.provider = DummyProvider()
        self.mission = MissionMobilityPlugin(self.protocol)

    def test_start_mission(self):
        self.mission.start_mission([
            (10, 10, 10)
        ])

        self.assertEqual(self.mission.current_waypoint, 0)
        self.assertFalse(self.mission.is_idle)
        self.assertFalse(self.mission.is_reversed)

        self.assertEqual(self.commands_sent[MobilityCommandType.GOTO_COORDS], 1)
        self.assertEqual(self.commands_sent[MobilityCommandType.SET_SPEED], 1)

    def test_mission_stop(self):
        self.mission.start_mission([
            (10, 10, 10)
        ])
        self.mission.stop_mission()

        self.assertIsNone(self.mission.current_waypoint)
        self.assertTrue(self.mission.is_idle)
        self.assertFalse(self.mission.is_reversed)

    def test_idle_before_start(self):
        self.assertTrue(self.mission.is_idle)
        self.assertEqual(len(self.commands_sent), 0)

    def test_waypoint_reached(self):
        self.mission.start_mission([
            (10, 10, 10),
            (20, 20, 20)
        ])

        self.protocol.handle_telemetry(Telemetry((10, 10, 10)))

        self.assertEqual(self.mission.current_waypoint, 1)
        self.assertEqual(self.commands_sent[MobilityCommandType.GOTO_COORDS], 2)

    def test_mission_finishes(self):
        self.mission.start_mission([
            (10, 10, 10)
        ])

        self.protocol.handle_telemetry(Telemetry((10, 10, 10)))

        self.assertIsNone(self.mission.current_waypoint)
        self.assertTrue(self.mission.is_idle)
        self.assertFalse(self.mission.is_reversed)

    def test_mission_restarts(self):
        self.mission = MissionMobilityPlugin(self.protocol,
                                             MissionMobilityConfiguration(loop_mission=LoopMission.RESTART))
        self.mission.start_mission([
            (10, 10, 10),
            (20, 20, 20),
            (30, 30, 30),
        ])

        self.protocol.handle_telemetry(Telemetry((10, 10, 10)))
        self.protocol.handle_telemetry(Telemetry((20, 20, 20)))
        self.protocol.handle_telemetry(Telemetry((30, 30, 30)))

        self.assertEqual(self.mission.current_waypoint, 0)
        self.assertEqual(self.commands_sent[MobilityCommandType.GOTO_COORDS], 4)

    def test_mission_reverses(self):
        self.mission = MissionMobilityPlugin(self.protocol,
                                             MissionMobilityConfiguration(loop_mission=LoopMission.REVERSE))
        self.mission.start_mission([
            (10, 10, 10),
            (20, 20, 20),
            (30, 30, 30),
        ])

        self.protocol.handle_telemetry(Telemetry((10, 10, 10)))
        self.protocol.handle_telemetry(Telemetry((20, 20, 20)))
        self.protocol.handle_telemetry(Telemetry((30, 30, 30)))

        self.assertEqual(self.mission.current_waypoint, 1)
        self.assertEqual(self.commands_sent[MobilityCommandType.GOTO_COORDS], 4)

    def test_set_reverse(self):
        self.mission = MissionMobilityPlugin(self.protocol,
                                             MissionMobilityConfiguration(loop_mission=LoopMission.REVERSE))

        self.mission.start_mission([
            (10, 10, 10),
            (20, 20, 20),
            (30, 30, 30),
        ])

        self.protocol.handle_telemetry(Telemetry((10, 10, 10)))
        self.mission.set_reversed(True)

        self.assertEqual(self.mission.current_waypoint, 0)
        self.assertTrue(self.mission.is_reversed)
        self.assertEqual(self.commands_sent[MobilityCommandType.GOTO_COORDS], 3)

    def test_set_waypoint(self):
        self.mission.start_mission([
            (10, 10, 10),
            (20, 20, 20),
            (30, 30, 30),
        ])

        self.mission.set_current_waypoint(2)
        self.assertEqual(self.mission.current_waypoint, 2)
        self.assertEqual(self.commands_sent[MobilityCommandType.GOTO_COORDS], 2)

    def test_set_waypoint_reversed(self):
        self.mission = MissionMobilityPlugin(self.protocol,
                                             MissionMobilityConfiguration(loop_mission=LoopMission.REVERSE))

        self.mission.start_mission([
            (10, 10, 10),
            (20, 20, 20),
            (30, 30, 30),
            (40, 40, 40)
        ])
        self.mission.set_current_waypoint(3)
        self.mission.set_reversed(True)

        self.mission.set_current_waypoint(1)
        self.assertEqual(self.mission.current_waypoint, 1)

        self.protocol.handle_telemetry(Telemetry((20, 20, 20)))

        self.assertEqual(self.mission.current_waypoint, 0)

        self.assertEqual(self.commands_sent[MobilityCommandType.GOTO_COORDS], 5)

    def test_set_waypoint_no_mission(self):
        with self.assertRaises(MissionMobilityPluginException):
            self.mission.set_current_waypoint(0)

    def test_set_waypoint_out_of_bounds(self):
        self.mission.start_mission([
            (10, 10, 10),
            (20, 20, 20),
            (30, 30, 30),
        ])

        with self.assertRaises(MissionMobilityPluginException):
            self.mission.set_current_waypoint(5)

        with self.assertRaises(MissionMobilityPluginException):
            self.mission.set_current_waypoint(-1)

    def test_set_reverse_no_reverses(self):
        self.mission.start_mission([
            (10, 10, 10),
            (20, 20, 20),
            (30, 30, 30),
        ])

        with self.assertRaises(MissionMobilityPluginException):
            self.mission.set_reversed(True)

    def test_set_reverse_no_mission(self):
        self.mission = MissionMobilityPlugin(self.protocol,
                                             MissionMobilityConfiguration(loop_mission=LoopMission.REVERSE))

        with self.assertRaises(MissionMobilityPluginException):
            self.mission.set_reversed(True)