"""Trajectory-following MPC example with visualization.

This script builds a GrADyS-SIM simulation with a single node controlled by
DynamicVelocityMobilityHandler and driven by TrajectoryMPCProtocol, which hands a fixed
takeoff-square-lap-landing trajectory to TrajectoryMPCPlugin. The plugin's MPC controller
computes the velocity commands needed to track it, subject to the handler's own speed and
acceleration limits.
"""

import importlib.util
import logging
from pathlib import Path

from gradysim.simulator.handler.mobility import DynamicVelocityMobilityHandler
from gradysim.simulator.handler.communication import CommunicationHandler, CommunicationMedium
from gradysim.simulator.handler.timer import TimerHandler
from gradysim.simulator.simulation import SimulationBuilder, SimulationConfiguration
from gradysim.simulator.handler.visualization import VisualizationConfiguration, VisualizationHandler

# Suppress websockets handshake warnings
logging.getLogger('websockets').setLevel(logging.CRITICAL)

SHOWCASE_DIR = Path(__file__).resolve().parent
PROTOCOL_PATH = SHOWCASE_DIR / "protocol.py"


def _load_trajectory_mpc_protocol():
    spec = importlib.util.spec_from_file_location(
        "trajectory_mpc_showcase_protocol",
        PROTOCOL_PATH,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load protocol module from {PROTOCOL_PATH}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    """Execute the trajectory MPC simulation."""
    protocol_module = _load_trajectory_mpc_protocol()
    trajectory_mpc_protocol = protocol_module.TrajectoryMPCProtocol
    dynamic_velocity_config = protocol_module.DYNAMIC_VELOCITY_CONFIG

    # Simulation parameters
    duration = 40  
    debug = False
    real_time = True  
    builder = SimulationBuilder(
        SimulationConfiguration(
            duration=duration,
            debug=debug,
            real_time=real_time
        )
    )

    medium = CommunicationMedium(transmission_range=200, delay=0.0, failure_rate=0.0)
    builder.add_handler(CommunicationHandler(medium))
    builder.add_handler(TimerHandler())


    print(
        "Mobility limits: "
        f"max_speed_xy={dynamic_velocity_config.max_speed_xy}, max_speed_z={dynamic_velocity_config.max_speed_z}, "
        f"max_acc_xy={dynamic_velocity_config.max_acc_xy}, max_acc_z={dynamic_velocity_config.max_acc_z}"
    )
    builder.add_handler(DynamicVelocityMobilityHandler(dynamic_velocity_config))

    vis_config = VisualizationConfiguration(open_browser=True, update_rate=0.1)
    builder.add_handler(VisualizationHandler(vis_config))

    builder.add_node(trajectory_mpc_protocol, (0, 0, 0))

    simulation = builder.build()
    print("=" * 60)
    print("Starting trajectory MPC simulation")
    print("Node follows a takeoff -> square lap -> landing trajectory")
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
