from counter_protocol import CounterProtocol
from simulator.node.handler.communication import CommunicationHandler, CommunicationMedium
from simulator.node.handler.mobility import MobilityHandler
from simulator.node.handler.timer import TimerHandler
from simulator.node.handler.visualization import VisualizationHandler, VisualizationConfiguration
from simulator.simulation import SimulationBuilder, SimulationConfiguration


# Trying a much larger simulation to illustrate a scenario
# where visual evaluation would be hard
config = SimulationConfiguration(
    duration=10000
)
builder = SimulationBuilder(config)

for _ in range(10):
    builder.add_node(CounterProtocol, (0, 0, 0))

builder.add_handler(TimerHandler())
builder.add_handler(CommunicationHandler())
builder.add_handler(MobilityHandler())

def assert_received_is_plausible(self, node: Node[CounterProtocol]):


simulation = builder.build()
simulation.start_simulation()

