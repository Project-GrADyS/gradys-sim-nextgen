"""Simple velocity-based mobility example with visualization.

This script builds a GrADyS-SIM simulation with a single node controlled by
InertialMobilityHandler. The node's velocity is commanded by InertialProtocol
in initialize(), and then changed periodically via a timer (every 10 seconds).

Initial node position is set in builder.add_node().
"""

import logging

from gradysim.simulator.handler.mobility import InertialMobilityConfiguration, InertialMobilityHandler

# Suppress websockets handshake warnings
logging.getLogger('websockets').setLevel(logging.CRITICAL)

from gradysim.simulator.handler.communication import CommunicationHandler, CommunicationMedium
from gradysim.simulator.handler.timer import TimerHandler
from gradysim.simulator.handler.visualization import VisualizationHandler, VisualizationConfiguration
from gradysim.simulator.simulation import SimulationBuilder, SimulationConfiguration
from protocol import InertialProtocol


# ============================================================
# Mobility presets (choose by editing ONE variable)
#
# Profiles: Cinematic, Survey, Cargo, Racing, Micro, Custom
# - For the first five profiles, values below are ALREADY the final values
#   (80% of the README table maxima, rounded to the same decimals as the table).
# - Custom uses the explicit values defined below (the original values).
# ============================================================

MOBILITY_PROFILE: str = "Cargo"  # Choose mobility profile here


CUSTOM_MOBILITY_CONFIG = InertialMobilityConfiguration(
    update_rate=0.01,        # Update every 0.01 seconds
    max_speed_xy=5.0,        # Max horizontal speed: 5 m/s
    max_speed_z=5.0,         # Max vertical speed: 5 m/s
    max_acc_xy=2.5,          # Max horizontal acceleration: 2.5 m/s²
    max_acc_z=2.5,           # Max vertical acceleration: 2.5 m/s²
    tau_xy=0.5,              # Optional: 1st-order horizontal tracking time constant (s)
    tau_z=0.8,               # Optional: 1st-order vertical tracking time constant (s)
    send_telemetry=True,     # Enable telemetry
    telemetry_decimation=1,  # Send telemetry every update
)


MOBILITY_PRESETS: dict[str, InertialMobilityConfiguration] = {
    "Cinematic": InertialMobilityConfiguration(
        update_rate=0.04,
        max_speed_xy=10.0,
        max_speed_z=5.0,
        max_acc_xy=4.0,
        max_acc_z=5.0,
        tau_xy=1.0,
        tau_z=1.2,
        send_telemetry=True,
        telemetry_decimation=1,
    ),
    "Survey": InertialMobilityConfiguration(
        update_rate=0.04,
        max_speed_xy=12.0,
        max_speed_z=2.0,
        max_acc_xy=3.0,
        max_acc_z=4.0,
        tau_xy=1.0,
        tau_z=1.4,
        send_telemetry=True,
        telemetry_decimation=1,
    ),
    "Cargo": InertialMobilityConfiguration(
        update_rate=0.04,
        max_speed_xy=8.0,
        max_speed_z=3.0,
        max_acc_xy=2.0,
        max_acc_z=4.0,
        tau_xy=1.2,
        tau_z=1.6,
        send_telemetry=True,
        telemetry_decimation=1,
    ),
    "Racing": InertialMobilityConfiguration(
        update_rate=0.02,
        max_speed_xy=32.0,
        max_speed_z=16.0,
        max_acc_xy=20.0,
        max_acc_z=20.0,
        tau_xy=0.3,
        tau_z=0.5,
        send_telemetry=True,
        telemetry_decimation=1,
    ),
    "Micro": InertialMobilityConfiguration(
        update_rate=0.02,
        max_speed_xy=5.0,
        max_speed_z=2.0,
        max_acc_xy=8.0,
        max_acc_z=10.0,
        tau_xy=0.6,
        tau_z=0.7,
        send_telemetry=True,
        telemetry_decimation=1,
    ),
    "Custom": CUSTOM_MOBILITY_CONFIG,
}


def main():
    """Execute the velocity mobility simulation."""
    
    # Simulation parameters
    duration = 50  # Simulation duration in seconds
    debug = False  # Simulation debug mode
    real_time = True  # Simulation real time mode - True to see movement in real-time
    builder = SimulationBuilder(
        SimulationConfiguration(
            duration=duration,
            debug=debug,
            real_time=real_time
        )
    )
    
    # Add the communication handler
    transmission_range = 200  # Communication transmission range in meters
    delay = 0.0  # Communication delay in seconds
    failure_rate = 0.0  # Communication failure rate in percentage
    medium = CommunicationMedium(
        transmission_range=transmission_range,
        delay=delay,
        failure_rate=failure_rate
    )
    builder.add_handler(CommunicationHandler(medium))
    
    # Add the timer handler
    builder.add_handler(TimerHandler())
    
    # Add the velocity mobility handler
    # Quadrotor trajectory-level model (velocity command tracking):
    # - The protocol commands a desired velocity v_des.
    # - The handler updates the effective velocity v with bounded acceleration.
    # - Optionally, tau_* adds a 1st-order lag (exponential-like response) before
    #   acceleration saturation, which often matches real quadrotor “feel”.
    #
    # Typical starting ranges (very approximate; tune for your platform):
    # - update_rate: 0.01–0.05 s
    # - max_speed_xy: 3–15 m/s
    # - max_speed_z:  1–8 m/s
    # - max_acc_xy:   2–8 m/s^2
    # - max_acc_z:    2–10 m/s^2
    # - tau_xy:       0.3–0.8 s (optional)
    # - tau_z:        0.5–1.2 s (optional)
    profile = (MOBILITY_PROFILE or "").strip()
    mobility_config = MOBILITY_PRESETS.get(profile)
    if mobility_config is None:
        valid = ", ".join(sorted(MOBILITY_PRESETS.keys()))
        raise ValueError(f"Unknown MOBILITY_PROFILE={MOBILITY_PROFILE!r}. Valid options: {valid}")

    print(
        "Mobility preset: "
        f"{profile} "
        f"(update_rate={mobility_config.update_rate}, "
        f"max_speed_xy={mobility_config.max_speed_xy}, max_speed_z={mobility_config.max_speed_z}, "
        f"max_acc_xy={mobility_config.max_acc_xy}, max_acc_z={mobility_config.max_acc_z}, "
        f"tau_xy={mobility_config.tau_xy}, tau_z={mobility_config.tau_z})"
    )
    velocity_handler = InertialMobilityHandler(mobility_config)
    builder.add_handler(velocity_handler)
    
    # Add the visualization handler
    vis_config = VisualizationConfiguration(
        open_browser=True,
        update_rate=0.1  # Update visualization every 0.1 seconds
    )
    builder.add_handler(VisualizationHandler(vis_config))
    
    # Add a single node at position (-25, -25, -25) - initial position
    builder.add_node(InertialProtocol, (-25, -25, -25))
    
    # Build and start simulation
    simulation = builder.build()
    print("=" * 60)
    print("Starting velocity mobility simulation")
    print("Node velocity is commanded by InertialProtocol (and changes every 10 seconds)")
    print("Starting position: (-25, -25, -25)")
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


if __name__ == "__main__":
    main()
