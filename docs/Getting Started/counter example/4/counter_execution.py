from counter_protocol import CounterProtocol
from gradysim.simulator import CommunicationHandler, CommunicationMedium
from gradysim.simulator.handler.mobility import MobilityHandler
from gradysim.simulator import TimerHandler
from gradysim.simulator.simulation import SimulationBuilder, SimulationConfiguration


config = SimulationConfiguration(
    duration=100
)
builder = SimulationBuilder(config)

# Adding 10 nodes on (0, 0, 0)
for _ in range(10):
    builder.add_node(CounterProtocol, (0, 0, 0))

builder.add_handler(TimerHandler())

# We will limit the communication range.
# This will help us see the effect of mobility on
# the nodes' position.
medium = CommunicationMedium(
    transmission_range=30
)

builder.add_handler(CommunicationHandler())

# Adding mobility handler
builder.add_handler(MobilityHandler())


simulation = builder.build()
simulation.start_simulation()

