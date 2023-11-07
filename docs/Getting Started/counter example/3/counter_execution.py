from counter_protocol import CounterProtocol
from gradysim.simulator import CommunicationHandler, CommunicationMedium
from gradysim.simulator import TimerHandler
from gradysim.simulator.simulation import SimulationBuilder, SimulationConfiguration

# This time we will be running the simulator for a longer time
# to help us visualize the effect of the medium configurations.
config = SimulationConfiguration(
    duration=100
)

builder = SimulationBuilder(config)

# Adding 10 nodes all on (0, 0, 0)
for _ in range(10):
    builder.add_node(CounterProtocol, (0, 0, 0))

# Adding a node far away, outside communication range from the others
builder.add_node(CounterProtocol, (50, 0, 0))


builder.add_handler(TimerHandler())

# Configuring a communication medium with limited transmission range,
# 1-second delay for message delivery and a 50% failure rate
medium = CommunicationMedium(
    transmission_range=30,
    delay=1,
    failure_rate=0.5
)
builder.add_handler(CommunicationHandler(medium))

# Calling the build functions creates a simulator from the previously
# specified options.
simulation = builder.build()

# The start_simulation() method will run the simulator until our 10-second
# limit is reached.
simulation.start_simulation()

