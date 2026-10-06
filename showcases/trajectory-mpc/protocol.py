"""
Protocol demonstrating trajectory following using the TrajectoryMPCPlugin: a Model Predictive
Controller that outputs velocity commands to DynamicVelocityMobilityHandler.
"""
from gradysim.protocol.interface import IProtocol
from gradysim.protocol.plugin.trajectory_mpc import (
    TrajectoryMPCPlugin,
    TrajectoryMPCConfiguration,
    TrajectoryPoint,
)
from gradysim.protocol.plugin.trajectory_mpc.reference import PiecewiseLinearReference
from gradysim.simulator.handler.mobility.dynamic_velocity.config import DynamicVelocityMobilityConfiguration
from gradysim.simulator.handler.mobility.dynamic_velocity.telemetry import DynamicVelocityTelemetry


DYNAMIC_VELOCITY_CONFIG = DynamicVelocityMobilityConfiguration(
    update_rate=0.01,
    max_speed_xy=10.0,
    max_speed_z=5.0,
    max_acc_xy=5.0,
    max_acc_z=5.0,
    tau_xy = 0.5,
    tau_z = 0.5,
)


def build_mpc_configuration(dynamic_velocity_config: DynamicVelocityMobilityConfiguration) -> TrajectoryMPCConfiguration:
    return TrajectoryMPCConfiguration.from_dynamic_velocity_config(
        dynamic_velocity_config,
        control_period=0.1,
        horizon_steps=15,
    )


class TrajectoryMPCProtocol(IProtocol):
    def __init__(self):
        super().__init__()
        self.node_id = None
        self.trajectory_plugin: TrajectoryMPCPlugin = None
        self.df = None

    def initialize(self):
        self.node_id = self.provider.get_id()

        if self.provider.get_id() == 0:
            TRAJECTORY = [
                TrajectoryPoint((0, 0, 0), 0.0),
                TrajectoryPoint((0, 0, 10), 5.0),    
                TrajectoryPoint((15, 0, 10), 10.0),  
                TrajectoryPoint((15, 15, 10), 15.0),  
                TrajectoryPoint((0, 15, 10), 20.0),  
                TrajectoryPoint((0, 0, 10), 25.0),  
                TrajectoryPoint((0, 0, 0), 30.0),    
            ]
        elif self.provider.get_id() == 1:
            TRAJECTORY = [
                TrajectoryPoint((0, 0, 0), 0.0),
                TrajectoryPoint((0, 0, 10), 5.0),    
                TrajectoryPoint((-15, 0, 10), 10.0),  
                TrajectoryPoint((-15, -15, 10), 15.0),  
                TrajectoryPoint((0, -15, 10), 20.0),  
                TrajectoryPoint((0, 0, 10), 25.0),  
                TrajectoryPoint((0, 0, 0), 30.0),    
            ]

        config = build_mpc_configuration(DYNAMIC_VELOCITY_CONFIG)
        self.trajectory_plugin = TrajectoryMPCPlugin(self, config)
        self._reference = PiecewiseLinearReference(TRAJECTORY)

        self.df = []

        print(f"Node {self.node_id} initialized")
        print(f"Starting trajectory with {len(TRAJECTORY)} waypoints "
              f"(duration {TRAJECTORY[-1].time:.1f}s)")

        self.trajectory_plugin.start_trajectory(self._reference)

    def handle_timer(self, timer: str):
        pass

    def handle_packet(self, message: str):
        pass

    def handle_telemetry(self, telemetry: DynamicVelocityTelemetry) -> None:
        t = self.provider.current_time()
        pos = telemetry.current_position
        vel = telemetry.current_velocity
        ref_pos, _ = self._reference.evaluate(t)

        self.df.append({
            "t": t,
            "x": pos[0], "y": pos[1], "z": pos[2],
            "vx": vel[0], "vy": vel[1], "vz": vel[2],
            "xr": ref_pos[0], "yr": ref_pos[1], "zr": ref_pos[2],
        })

    def finish(self):
        if self.trajectory_plugin is not None:
            print(f"Node {self.node_id}: trajectory finished = {self.trajectory_plugin.is_finished}")

        if self.df is None or len(self.df) < 2:
            return

        try:
            import matplotlib.pyplot as plt

            times = [r["t"] for r in self.df]
            xs, ys, zs = [r["x"] for r in self.df], [r["y"] for r in self.df], [r["z"] for r in self.df]
            xrs, yrs, zrs = [r["xr"] for r in self.df], [r["yr"] for r in self.df], [r["zr"] for r in self.df]
            vx, vy, vz = [r["vx"] for r in self.df], [r["vy"] for r in self.df], [r["vz"] for r in self.df]

            fig, axes = plt.subplots(1, 3, figsize=(12, 5.5))
            ax_top, ax_pos, ax_vel = axes

            ax_top.plot(xrs, yrs, linestyle="--", color="gray", label="reference path")
            ax_top.plot(xs, ys, label="actual path")
            ax_top.set_xlabel("x (m)")
            ax_top.set_ylabel("y (m)")
            ax_top.set_title("Top-down path")
            ax_top.axis("equal")
            ax_top.grid(True)
            ax_top.legend(loc="best")

            for values, ref_values, label, color in (
                (xs, xrs, "x", "tab:blue"),
                (ys, yrs, "y", "tab:orange"),
                (zs, zrs, "z", "tab:green"),
            ):
                ax_pos.plot(times, values, label=label, color=color)
                ax_pos.plot(times, ref_values, linestyle="--", color=color, alpha=0.6)
            ax_pos.set_xlabel("time (s)")
            ax_pos.set_ylabel("position (m)")
            ax_pos.set_title("Position vs. reference (dashed)")
            ax_pos.grid(True)
            ax_pos.legend(loc="best")

            for values, label, color in (
                (vx, "vx", "tab:blue"),
                (vy, "vy", "tab:orange"),
                (vz, "vz", "tab:gray"),
            ):
                ax_vel.plot(times, values, label=label, color=color)
            ax_vel.set_xlabel("time (s)")
            ax_vel.set_ylabel("velocity (m/s)")
            ax_vel.set_title("Velocity")
            ax_vel.grid(True)

            fig.suptitle(f"Node {self.node_id}: trajectory MPC tracking")
            plt.tight_layout(rect=(0, 0, 1, 0.96))
            plt.show()
        except ImportError:
            print("matplotlib not available; skipping plots")
