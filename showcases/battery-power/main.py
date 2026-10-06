"""Battery power showcase with real-time visualization.

Builds a GrADyS-SIM simulation with three UAVs that share the exact same physical specs
(BatteryPowerConfiguration) but fly at different speeds along different axes:

    Node 0 - "Vertical-Climber": moves only along the z axis.
    Node 1 - "Forward-Cruiser":  moves only along the x body-frame axis.
    Node 2 - "Diagonal-Flyer":   moves along both x and z simultaneously.

The simulation runs in real_time mode for 50 seconds. Each UAV logs its own battery
level to the console once a second and mirrors it into the live browser visualization.
Once the run finishes a comparison plot of all three battery curves is shown.
"""

import importlib.util
import logging
from pathlib import Path

from gradysim.simulator.handler.mobility import (
    DynamicVelocityMobilityConfiguration,
    DynamicVelocityMobilityHandler,
)
from gradysim.simulator.handler.communication import CommunicationHandler, CommunicationMedium
from gradysim.simulator.handler.timer import TimerHandler
from gradysim.simulator.simulation import SimulationBuilder, SimulationConfiguration
from gradysim.simulator.handler.visualization import VisualizationConfiguration, VisualizationHandler

# Suppress websockets handshake warnings
logging.getLogger('websockets').setLevel(logging.CRITICAL)

SHOWCASE_DIR = Path(__file__).resolve().parent
PROTOCOL_PATH = SHOWCASE_DIR / "protocol.py"


def _load_battery_protocol():
    """Load the showcase-local protocol module without relying on sys.path ordering."""
    spec = importlib.util.spec_from_file_location(
        "battery_power_showcase_protocol",
        PROTOCOL_PATH,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load protocol module from {PROTOCOL_PATH}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _plot_results(results: dict):
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not available; skipping plot")
        return

    if not results:
        print("No battery history collected; skipping plot")
        return

    fig, ax = plt.subplots(figsize=(9, 5))
    for node_id in sorted(results):
        data = results[node_id]
        history = data["history"]
        if not history:
            continue
        times = [row["t"] for row in history]
        levels = [row["battery_pct"] for row in history]
        vx, vy, vz = data["velocity"]
        ax.plot(times, levels, marker="o", markersize=3,
                label=f"UAV {node_id} - {data['name']} (v={vx},{vy},{vz} m/s)")

    ax.set_xlabel("time (s)")
    ax.set_ylabel("battery level (%)")
    ax.set_title("Battery level over time - same specs, different speeds/axes")
    ax.grid(True)
    ax.legend(loc="best")
    plt.tight_layout()
    plt.show()


def main():
    """Execute the battery power showcase simulation."""
    protocol_module = _load_battery_protocol()
    battery_protocol = protocol_module.BatteryUAVProtocol

    duration = 600   
    debug = False
    real_time = False 
    builder = SimulationBuilder(
        SimulationConfiguration(
            duration=duration,
            debug=debug,
            real_time=real_time,
        )
    )

    medium = CommunicationMedium(transmission_range=200, delay=0.0, failure_rate=0.0)
    builder.add_handler(CommunicationHandler(medium))

    builder.add_handler(TimerHandler())

    # BatteryPowerPlugin requires DynamicVelocityMobilityHandler for velocity telemetry.
    mobility_config = DynamicVelocityMobilityConfiguration(
        update_rate=0.05,
        max_speed_xy=10.0,
        max_speed_z=10.0,
        max_acc_xy=3.0,
        max_acc_z=3.0,
        send_telemetry=True,
    )
    builder.add_handler(DynamicVelocityMobilityHandler(mobility_config))

    vis_config = VisualizationConfiguration(open_browser=True, update_rate=0.1)
    builder.add_handler(VisualizationHandler(vis_config))

    builder.add_node(battery_protocol, (0, 0, 0))
    builder.add_node(battery_protocol, (0, 0, 0))
    builder.add_node(battery_protocol, (0, 0, 0))

    simulation = builder.build()
    print("=" * 60)
    print("Starting battery power showcase")
    print("UAV 0 - Vertical-Climber: z axis only, 2 m/s")
    print("UAV 1 - Forward-Cruiser:  x body frame only, 4 m/s")
    print("UAV 2 - Diagonal-Flyer:   x and z together, 3 m/s each")
    print("Same battery/aero specs on all three - watch battery drain differ by profile")
    print("Visualization will open in browser automatically")
    print("=" * 60)
    try:
        simulation.start_simulation()
    except (BrokenPipeError, EOFError) as e:
        logging.getLogger(__name__).debug(f"Ignored visualization shutdown error: {e}")
    finally:
        print("=" * 60)
        print("Simulation completed!")
        print("=" * 60)

    _plot_results(protocol_module.RESULTS)


if __name__ == "__main__":
    main()
