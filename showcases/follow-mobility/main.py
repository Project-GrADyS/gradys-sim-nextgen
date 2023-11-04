from typing import List

from protocol import LeaderProtocol, FollowerProtocol
from gradys.simulator.handler.communication import CommunicationHandler
from gradys.simulator.handler.mobility import MobilityHandler
from gradys.simulator.handler.timer import TimerHandler
from gradys.simulator.handler.visualization import VisualizationHandler
from gradys.simulator.simulation import SimulationBuilder, SimulationConfiguration, PositionScheme

if __name__ == '__main__':
    builder = SimulationBuilder(SimulationConfiguration(duration=30, debug=True, real_time=True))
    builder.add_handler(CommunicationHandler())
    builder.add_handler(TimerHandler())
    builder.add_handler(MobilityHandler())
    builder.add_handler(VisualizationHandler())

    builder.add_node(LeaderProtocol, (0, 0, 0))
    for _ in range(10):
        builder.add_node(FollowerProtocol, PositionScheme.random((-5, 5), (-5, 5), (0, 5)))

    simulation = builder.build()
    simulation.start_simulation()
