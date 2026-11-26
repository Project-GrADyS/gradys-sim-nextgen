"""
Protocol demonstrating BatteryPowerPlugin on three UAVs that share the same physical
specs (same BatteryPowerConfiguration) but fly different speeds along different axes:

    Node 0 - "Vertical-Climber": moves only along the z axis (climbs/descends).
    Node 1 - "Forward-Cruiser":  moves only along the x body-frame axis.
    Node 2 - "Diagonal-Flyer":   moves along both x and z simultaneously.

Each UAV reverses its direction periodically so it stays within a bounded volume for
the whole run instead of flying off in a straight line. Battery level is logged to the
console once a second (the simulation runs with real_time=True, so that is roughly once
every real-world second) and mirrored into `tracked_variables` so it is also visible live
in the browser visualization.
"""
from typing import Dict, List

from gradysim.protocol.interface import IProtocol
from gradysim.protocol.messages.mobility import SetVelocityMobilityCommand
from gradysim.protocol.plugin.battery_power import BatteryPowerPlugin, BatteryPowerConfiguration
from gradysim.simulator.handler.mobility.dynamic_velocity.telemetry import DynamicVelocityTelemetry

import numpy as np


SHARED_BATTERY_CONFIG = BatteryPowerConfiguration()

LOG_PERIOD = 1.0   
BOUNCE_PERIOD = 10.0 

UAV_SPECS: Dict[int, dict] = {
    0: {"name": "Vertical-Climber", "velocity": (0.0, 0.0, 10.0)},
    1: {"name": "Forward-Cruiser", "velocity": (10.0, 0.0, 0.0)},
    2: {"name": "Diagonal-Flyer", "velocity": (5*np.sqrt(2), 0.0,5*np.sqrt(2))},
}

RESULTS: Dict[int, dict] = {}


class BatteryUAVProtocol(IProtocol):
    """UAV protocol that flies a fixed velocity profile while BatteryPowerPlugin tracks
    its battery drain."""

    def __init__(self):
        super().__init__()
        self.node_id = None
        self.name = None
        self.base_velocity = (0.0, 0.0, 0.0)
        self.direction = 1
        self.battery: BatteryPowerPlugin = None
        self.history: List[dict] = []

    def _current_velocity(self):
        vx, vy, vz = self.base_velocity
        return (vx * self.direction, vy, vz * self.direction)

    def _send_velocity(self):
        vx, vy, vz = self._current_velocity()
        self.provider.send_mobility_command(SetVelocityMobilityCommand(vx, vy, vz))

    def initialize(self):
        self.node_id = self.provider.get_id()
        spec = UAV_SPECS[self.node_id]
        self.name = spec["name"]
        self.base_velocity = spec["velocity"]

        self.battery = BatteryPowerPlugin(self, SHARED_BATTERY_CONFIG)

        self._send_velocity()

        print(f"UAV {self.node_id} ({self.name}) initialized, "
              f"velocity={self._current_velocity()} m/s")

        self.provider.schedule_timer("log_timer", self.provider.current_time() + LOG_PERIOD)
        self.provider.schedule_timer("bounce_timer", self.provider.current_time() + BOUNCE_PERIOD)

    def handle_timer(self, timer: str):
        if timer == "log_timer":
            t = self.provider.current_time()
            pct = self.battery.battery_status * 100

            print(f"[t={t:5.1f}s] UAV {self.node_id} ({self.name}): battery={pct:5.1f}%")

            self.history.append({"t": t, "battery_pct": pct})

            self.provider.tracked_variables["battery_pct"] = round(pct, 1)
            self.provider.tracked_variables["name"] = self.name

            self.provider.schedule_timer("log_timer", t + LOG_PERIOD)

        elif timer == "bounce_timer":
            self.direction *= -1
            self._send_velocity()
            print(f"UAV {self.node_id} ({self.name}) reversing, "
                  f"velocity={self._current_velocity()} m/s")

            self.provider.schedule_timer("bounce_timer", self.provider.current_time() + BOUNCE_PERIOD)

    def handle_packet(self, message: str):
        pass

    def handle_telemetry(self, telemetry: DynamicVelocityTelemetry) -> None:
        pass

    def finish(self):
        pct = self.battery.battery_status * 100
        print(f"UAV {self.node_id} ({self.name}) final battery level: {pct:.1f}%")

        RESULTS[self.node_id] = {
            "name": self.name,
            "velocity": self.base_velocity,
            "history": self.history,
        }
