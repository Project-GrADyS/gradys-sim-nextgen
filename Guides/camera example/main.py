import random

from gradysim.simulator.handler.mobility import MobilityHandler
from gradysim.simulator.handler.timer import TimerHandler
from gradysim.simulator.handler.visualization import VisualizationHandler
from gradysim.simulator.simulation import SimulationConfiguration, SimulationBuilder
from protocol import PointOfInterest, Drone


def main():
    # Configuring simulation
    config = SimulationConfiguration(
        duration=200
    )
    builder = SimulationBuilder(config)

    builder.add_handler(TimerHandler())
    builder.add_handler(MobilityHandler())
    builder.add_handler(VisualizationHandler())

    # Instantiating a bunch of ground sensors
    for _ in range(100):
        builder.add_node(PointOfInterest,
                         (random.randint(-50, 50), random.randint(-50, 50), 0))

    # Instantiating 4 UAVs at (0,0,0)
    for _ in range(4):
        builder.add_node(Drone, (0, 0, 0))

    # Building & starting
    simulation = builder.build()
    simulation.start_simulation()


if __name__ == "__main__":
    main()
