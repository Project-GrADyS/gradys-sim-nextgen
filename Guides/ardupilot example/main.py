import sys

from gradysim.simulator.handler.communication import CommunicationHandler, CommunicationMedium
from gradysim.simulator.handler.ardupilot_mobility import ArdupilotMobilityHandler, ArdupilotMobilityConfiguration
from gradysim.simulator.handler.timer import TimerHandler
from gradysim.simulator.simulation import SimulationBuilder, SimulationConfiguration
from simple_protocol import SimpleSensorProtocol, SimpleUAVProtocol, SimpleGroundStationProtocol


def main():
    # Path to your local clone of the Ardupilot repository
    ardupilot_path = sys.argv[1] if len(sys.argv) > 1 else None

    # Configuring simulation - real_time is required for ArdupilotMobilityHandler
    config = SimulationConfiguration(
        duration=300,
        real_time=True
    )
    builder = SimulationBuilder(config)

    # Configuring the Ardupilot mobility handler
    ardupilot_config = ArdupilotMobilityConfiguration(
        simulate_drones=True,
        ardupilot_path=ardupilot_path,
        starting_api_port=8000,
        update_rate=0.5,
        default_speed=10,
        generate_report=True
    )

    # Adding required handlers
    builder.add_handler(TimerHandler())
    builder.add_handler(CommunicationHandler(CommunicationMedium(
        transmission_range=30
    )))
    builder.add_handler(ArdupilotMobilityHandler(ardupilot_config))

    # Instantiating 4 sensors in fixed positions around the origin
    builder.add_node(SimpleSensorProtocol, (100, 0, 0))
    builder.add_node(SimpleSensorProtocol, (0, 100, 0))
    builder.add_node(SimpleSensorProtocol, (-100, 0, 0))
    builder.add_node(SimpleSensorProtocol, (0, -100, 0))

    # Instantiating 4 UAVs at the origin
    builder.add_node(SimpleUAVProtocol, (0, 0, 0))
    builder.add_node(SimpleUAVProtocol, (0, 0, 0))
    builder.add_node(SimpleUAVProtocol, (0, 0, 0))
    builder.add_node(SimpleUAVProtocol, (0, 0, 0))

    # Instantiating ground station at the origin
    builder.add_node(SimpleGroundStationProtocol, (0, 0, 0))

    # Building & starting
    simulation = builder.build()
    simulation.start_simulation()


if __name__ == "__main__":
    main()
