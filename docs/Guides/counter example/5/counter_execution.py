from counter_protocol import CounterProtocol
from gradysim.simulator.handler.communication import CommunicationMedium, CommunicationHandler
from gradysim.simulator.handler.mobility import MobilityHandler
from gradysim.simulator.handler.timer import TimerHandler
from gradysim.simulator.handler.visualization import VisualizationHandler
from gradysim.simulator.simulation import SimulationBuilder, SimulationConfiguration


def main():
    # To enhance our viewing experience we are setting the simulator
    # to real-time mode. This means that the simulator will run
    # approximately synchronized with real-time, enabling us to see
    # the nodes moving properly. We are also decreasing the total
    # simulator time, so we don't have to wait for that long
    config = SimulationConfiguration(
        duration=30,
        real_time=True
    )
    builder = SimulationBuilder(config)

    for _ in range(10):
        builder.add_node(CounterProtocol, (0, 0, 0))

    builder.add_handler(TimerHandler())

    medium = CommunicationMedium(
        transmission_range=30
    )
    builder.add_handler(CommunicationHandler(medium))

    builder.add_handler(MobilityHandler())

    # Adding visualization handler to the simulator
    builder.add_handler(VisualizationHandler())

    simulation = builder.build()
    simulation.start_simulation()


if __name__ == "__main__":
    main()
