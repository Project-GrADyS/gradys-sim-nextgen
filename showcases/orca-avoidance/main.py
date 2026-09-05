"""ORCA avoidance showcase with visualization, three scenarios run one after another.

1. Two drones head-to-head, on paths offset just enough that they aren't perfectly aligned (a
   perfectly collinear head-on approach is a degenerate case for the ORCA solve).
2. Three drones in the same kind of head-on encounter.
3. The original four-drone square shuttle: each drone flies to the diagonally opposite corner of a
   square and back, crossing paths near the center on every leg.
"""

import importlib.util
import logging
import time
from pathlib import Path
from typing import List, Optional, Sequence

from gradysim.simulator.handler.mobility import DynamicVelocityMobilityHandler
from gradysim.simulator.handler.communication import CommunicationHandler, CommunicationMedium
from gradysim.simulator.handler.timer import TimerHandler
from gradysim.simulator.simulation import SimulationBuilder, SimulationConfiguration
from gradysim.simulator.handler.visualization import VisualizationConfiguration, VisualizationHandler

# Suppress websockets handshake warnings
logging.getLogger('websockets').setLevel(logging.CRITICAL)

SHOWCASE_DIR = Path(__file__).resolve().parent
PROTOCOL_PATH = SHOWCASE_DIR / "protocol.py"

TRANSMISSION_RANGE = 40.0

HEAD_ON_DURATION = 35


def _load_protocol_module():
    spec = importlib.util.spec_from_file_location(
        "orca_avoidance_showcase_protocol",
        PROTOCOL_PATH,
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load protocol module from {PROTOCOL_PATH}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _reset_root_logging_handlers() -> None:
    root_logger = logging.getLogger()
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)


def _plot_results(
    protocols: Sequence,
    inflation_radius: float,
    title: str,
    square_size: Optional[float] = None,
) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not available; skipping plots")
        return

    colors = ["tab:blue", "tab:orange", "tab:green", "tab:red"]

    fig, (ax_top, ax_z, ax_conflicts) = plt.subplots(1, 3, figsize=(16, 5.5))

    if square_size is not None:
        square_x = [0, square_size, square_size, 0, 0]
        square_y = [0, 0, square_size, square_size, 0]
        ax_top.plot(square_x, square_y, linestyle=":", color="gray", label="square corners")

    for protocol, color in zip(protocols, colors):
        xs = [row["x"] for row in protocol.df]
        ys = [row["y"] for row in protocol.df]
        colliding = [row["colliding"] for row in protocol.df]

        ax_top.plot(xs, ys, color=color, label=f"node {protocol.node_id}", linewidth=1.2)
        avoiding_x = [x for x, c in zip(xs, colliding) if c]
        avoiding_y = [y for y, c in zip(ys, colliding) if c]
        ax_top.scatter(avoiding_x, avoiding_y, color=color, s=8, zorder=3)

    ax_top.set_xlabel("x (m)")
    ax_top.set_ylabel("y (m)")
    ax_top.set_title("Top-down paths (dots = avoiding)")
    ax_top.axis("equal")
    ax_top.grid(True)
    ax_top.legend(loc="best", fontsize=8)

    for protocol, color in zip(protocols, colors):
        ts = [row["t"] for row in protocol.df]
        zs = [row["z"] for row in protocol.df]
        ax_z.plot(ts, zs, color=color, label=f"node {protocol.node_id}")
    ax_z.set_xlabel("time (s)")
    ax_z.set_ylabel("z (m)")
    ax_z.set_title("Altitude over time")
    ax_z.grid(True)
    ax_z.legend(loc="best", fontsize=8)

    common_length = min((len(protocol.df) for protocol in protocols), default=0)
    if common_length > 0:
        ts = [row["t"] for row in protocols[0].df[:common_length]]
        conflict_counts = [
            sum(1 for protocol in protocols if protocol.df[i]["colliding"])
            for i in range(common_length)
        ]
        ax_conflicts.step(ts, conflict_counts, where="post", color="black")
    ax_conflicts.set_xlabel("time (s)")
    ax_conflicts.set_ylabel("# nodes avoiding")
    ax_conflicts.set_title("Simultaneous avoidance episodes")
    ax_conflicts.set_yticks(range(len(protocols) + 1))
    ax_conflicts.grid(True)

    fig.suptitle(f"{title} (inflation radius = {inflation_radius:.1f} m)")
    plt.tight_layout(rect=(0, 0, 1, 0.95))
    plt.show()


def _run_head_on_scenario(protocol_module, count: int, scenario_label: str) -> None:
    _reset_root_logging_handlers()

    protocol_cls = protocol_module.HeadOnOrcaProtocol
    dynamic_velocity_config = protocol_module.DYNAMIC_VELOCITY_CONFIG

    paths = protocol_module.build_head_on_paths(count)
    protocol_module.HEAD_ON_PATHS = paths

    builder = SimulationBuilder(
        SimulationConfiguration(duration=HEAD_ON_DURATION, debug=False, real_time=True)
    )

    medium = CommunicationMedium(transmission_range=TRANSMISSION_RANGE, delay=0.0, failure_rate=0.0)
    builder.add_handler(CommunicationHandler(medium))
    builder.add_handler(TimerHandler())
    builder.add_handler(DynamicVelocityMobilityHandler(dynamic_velocity_config))

    vis_config = VisualizationConfiguration(open_browser=True, update_rate=0.1)
    builder.add_handler(VisualizationHandler(vis_config))

    node_ids = [builder.add_node(protocol_cls, start) for start, _target in paths]

    simulation = builder.build()
    print("=" * 60)
    print(scenario_label)
    print(
        f"{count} drones fly head-to-head towards the opposite side of a circle, offset "
        "slightly so no two paths perfectly overlap"
    )
    print("Visualization will open in browser automatically")
    print("=" * 60)
    try:
        simulation.start_simulation()
    except (BrokenPipeError, EOFError) as e:
        logging.getLogger(__name__).debug(f"Ignored visualization shutdown error: {e}")
    finally:
        print("=" * 60)
        print(f"{scenario_label} completed!")
        print("=" * 60)

    time.sleep(1.0)

    protocols = [simulation.get_node(node_id).protocol_encapsulator.protocol for node_id in node_ids]
    orca_config = protocol_module.build_orca_configuration(dynamic_velocity_config)
    _plot_results(protocols, orca_config.inflation_radius, scenario_label)


def _run_square_shuttle_scenario(protocol_module) -> None:
    _reset_root_logging_handlers()

    protocol_cls = protocol_module.SquareShuttleOrcaProtocol
    dynamic_velocity_config = protocol_module.DYNAMIC_VELOCITY_CONFIG
    corners = protocol_module.CORNERS
    square_size = protocol_module.SQUARE_SIZE

    # Each node stops after its second (return) leg rather than shuttling indefinitely, so
    # duration only needs to cover ~2 legs plus the start-time stagger.
    duration = 55
    builder = SimulationBuilder(
        SimulationConfiguration(duration=duration, debug=False, real_time=True)
    )

    medium = CommunicationMedium(transmission_range=TRANSMISSION_RANGE, delay=0.0, failure_rate=0.0)
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

    node_ids: List[int] = [builder.add_node(protocol_cls, corners[i]) for i in range(4)]

    simulation = builder.build()
    print("=" * 60)
    print("Scenario 3/3: square-shuttle ORCA avoidance")
    print("Four nodes shuttle between opposite corners, crossing paths at the center")
    print("Visualization will open in browser automatically")
    print("=" * 60)
    try:
        simulation.start_simulation()
    except (BrokenPipeError, EOFError) as e:
        logging.getLogger(__name__).debug(f"Ignored visualization shutdown error: {e}")
    finally:
        print("=" * 60)
        print("Scenario 3/3 completed!")
        print("=" * 60)

    protocols = [simulation.get_node(node_id).protocol_encapsulator.protocol for node_id in node_ids]
    orca_config = protocol_module.build_orca_configuration(dynamic_velocity_config)
    _plot_results(protocols, orca_config.inflation_radius, "Square-shuttle ORCA avoidance", square_size=square_size)


def main():
    """Runs the three ORCA avoidance scenarios one after another."""
    protocol_module = _load_protocol_module()

    _run_head_on_scenario(protocol_module, count=2, scenario_label="Scenario 1/3: two-drone head-on ORCA avoidance")
    _run_head_on_scenario(protocol_module, count=3, scenario_label="Scenario 2/3: three-drone head-on ORCA avoidance")
    _run_square_shuttle_scenario(protocol_module)


if __name__ == "__main__":
    main()
