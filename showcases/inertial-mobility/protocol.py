"""
Protocol demonstrating velocity-based mobility using VelocityMobilityHandler.

Uses direct method calls instead of standard GrADyS mobility commands.
"""

from gradysim.protocol.interface import IProtocol
from gradysim.protocol.messages.mobility import SetVelocityMobilityCommand
from gradysim.protocol.messages.telemetry import Telemetry
from gradysim.simulator.handler.mobility.intertial.telemetry import InertialTelemetry


class InertialProtocol(IProtocol):
    """Protocol that commands velocity through VelocityMobilityHandler."""

    def __init__(self):
        super().__init__()
        self.node_id = None
        self.initial_position = None
        self.current_position = None
        self.current_velocity = None
        self.final_position = None
        self.final_velocity = None
        self.desired_velocity = None
        self.df = None

        self._velocity_setpoints = [
            (0.0, 5.0, 5.0),
            (5.0, 0.0, -5.0),
            (0.0, -5.0, 5.0),
            (-5.0, 0.0, -5.0),
            (0.0, 0.0, 0.0),
        ]
        self._velocity_setpoint_index = 0

    def _set_velocity(self, velocity: tuple[float, float, float]):
        """Helper method to set velocity and print info."""
        message = SetVelocityMobilityCommand(*velocity)
        self.provider.send_mobility_command(message)

        # Calculate and display velocity magnitude and direction
        vx, vy, vz = velocity
        speed = (vx**2 + vy**2 + vz**2)**0.5

        if abs(vy) > abs(vx) and abs(vy) > abs(vz):
            direction = "north" if vy > 0 else "south"
        elif abs(vx) > abs(vy) and abs(vx) > abs(vz):
            direction = "east" if vx > 0 else "west"
        else:
            direction = "vertical"

        print(f"Node {self.node_id} initialized")
        print(f"Velocity commanded: {speed:.2f} m/s heading {direction}")

    def initialize(self):
        """Initialize and command initial velocity."""
        self.node_id = self.provider.get_id()
        self._velocity_setpoint_index = 0
        self.desired_velocity = self._velocity_setpoints[self._velocity_setpoint_index]

        self._set_velocity(self.desired_velocity)

        self.df = []

        self.schedule_change_speed_timer(10.0) # Schedule next change speed in 10 seconds

    def schedule_change_speed_timer(self, timeout: float = None):
        self.provider.schedule_timer("change_speed_timer", self.provider.current_time() + timeout)

    def handle_timer(self, timer: str):
        """Handle timer events."""
        if timer == "change_speed_timer":
            self._velocity_setpoint_index = min(
                self._velocity_setpoint_index + 1,
                len(self._velocity_setpoints) - 1,
            )
            self.desired_velocity = self._velocity_setpoints[self._velocity_setpoint_index]
            self._set_velocity(self.desired_velocity)
            self.schedule_change_speed_timer(10.0) # Schedule next speed change in 10 seconds

    def handle_packet(self, message: str):
        """Handle incoming packets."""
        pass

    def handle_telemetry(self, telemetry: InertialTelemetry) -> None:
        """Collect time, position and velocity on telemetry."""
        t = self.provider.current_time()
        pos = telemetry.current_position
        vel = telemetry.current_velocity
        vdes = self.desired_velocity

        self.df.append({
            "t": t,
            "x": pos[0], "y": pos[1], "z": pos[2],
            "vx": vel[0], "vy": vel[1], "vz": vel[2],
            "vxd": vdes[0], "vyd": vdes[1], "vzd": vdes[2],
        })

        self.current_velocity = vel
        self.current_position = pos

    def finish(self):
        """Called when simulation ends."""
        # Fetch final state from handler
        final_position = self.current_position
        final_velocity = self.current_velocity

        if final_position is None:
            return

        # Calculate actual movement
        dx = final_position[0] - self.initial_position[0]
        dy = final_position[1] - self.initial_position[1]
        dz = final_position[2] - self.initial_position[2]
        net_displacement = (dx**2 + dy**2 + dz**2)**0.5

        print()
        print("=" * 60)
        print("SIMULATION RESULTS")
        print("=" * 60)
        print(f"Node {self.node_id}")
        print(f"  Initial position: ({self.initial_position[0]:.2f}, {self.initial_position[1]:.2f}, {self.initial_position[2]:.2f})")
        print(f"  Final position:   ({final_position[0]:.2f}, {final_position[1]:.2f}, {final_position[2]:.2f})")
        print(f"  Movement vector:  ({dx:.2f}, {dy:.2f}, {dz:.2f})")
        print(f"  Net displacement: {net_displacement:.2f} m")
        if final_velocity:
            final_speed = (final_velocity[0]**2 + final_velocity[1]**2 + final_velocity[2]**2)**0.5
            print(f"  Final velocity:   {final_speed:.2f} m/s")
        print("=" * 60)

        # Plot position and velocity over time
        if self.df is not None and len(self.df) > 1:
            try:
                import matplotlib.pyplot as plt

                # Convert list-of-dicts into separate lists for plotting
                times = [r["t"] for r in self.df]
                xs = [r["x"] for r in self.df]
                ys = [r["y"] for r in self.df]
                zs = [r["z"] for r in self.df]

                vxs = [r["vx"] for r in self.df]
                vys = [r["vy"] for r in self.df]
                vzs = [r["vz"] for r in self.df]

                vxds = [r["vxd"] for r in self.df]
                vyds = [r["vyd"] for r in self.df]
                vzds = [r["vzd"] for r in self.df]

                fig, axes = plt.subplots(4, 1, sharex=True, figsize=(10, 9))
                ax_pos, ax_vx, ax_vy, ax_vz = axes

                x_line = ax_pos.plot(times, xs, label="x")[0]
                y_line = ax_pos.plot(times, ys, label="y")[0]
                z_line = ax_pos.plot(times, zs, label="z")[0]
                ax_pos.set_ylabel("position (m)")
                ax_pos.grid(True)
                ax_pos.legend(loc="best")

                vx_meas_line = ax_vx.plot(
                    times,
                    vxs,
                    label="vx",
                    color=x_line.get_color(),
                )[0]
                ax_vx.plot(
                    times,
                    vxds,
                    label="vx_des",
                    linestyle="--",
                    drawstyle="steps-post",
                    color=vx_meas_line.get_color(),
                )
                ax_vx.set_ylabel("vx (m/s)")
                ax_vx.grid(True)
                ax_vx.legend(loc="best")

                vy_meas_line = ax_vy.plot(
                    times,
                    vys,
                    label="vy",
                    color=y_line.get_color(),
                )[0]
                ax_vy.plot(
                    times,
                    vyds,
                    label="vy_des",
                    linestyle="--",
                    drawstyle="steps-post",
                    color=vy_meas_line.get_color(),
                )
                ax_vy.set_ylabel("vy (m/s)")
                ax_vy.grid(True)
                ax_vy.legend(loc="best")

                vz_meas_line = ax_vz.plot(
                    times,
                    vzs,
                    label="vz",
                    color=z_line.get_color(),
                )[0]
                ax_vz.plot(
                    times,
                    vzds,
                    label="vz_des",
                    linestyle="--",
                    drawstyle="steps-post",
                    color=vz_meas_line.get_color(),
                )
                ax_vz.set_xlabel("time (s)")
                ax_vz.set_ylabel("vz (m/s)")
                ax_vz.grid(True)
                ax_vz.legend(loc="best")

                fig.suptitle(f"Node {self.node_id}: position and velocity vs time")
                plt.tight_layout(rect=(0, 0, 1, 0.96))
                plt.show()
            except ImportError:
                print("matplotlib not available; skipping plots")
