from simulator.node.handler.communication import CommunicationHandler
from simulator.node.handler.mobility import MobilityHandler, MobilityConfiguration
from simulator.node.handler.timer import TimerHandler
from simulator.simulation import SimulationBuilder, SimulationConfiguration
from ping import PingProtocol


if __name__ == '__main__':
    builder = SimulationBuilder(SimulationConfiguration(duration=10, debug=True, real_time=True))
    builder.add_handler(CommunicationHandler())
    builder.add_handler(TimerHandler())
    builder.add_handler(MobilityHandler(MobilityConfiguration(visualization=True)))

    builder.add_node(PingProtocol, (0, 0, 0))
    builder.add_node(PingProtocol, (1, 1, 0))

    simulation = builder.build()
    simulation.start_simulation()
