from counter_protocol import CounterProtocol
from simulator.node.handler.communication import CommunicationHandler
from simulator.node.handler.timer import TimerHandler
from simulator.simulation import SimulationBuilder, SimulationConfiguration

# Configuring the simulation. The only option that interests us
# is limiting the simulation to 10 real-world seconds.
config = SimulationConfiguration(
    duration=10
)
# Instantiating the simulation builder with the created config
builder = SimulationBuilder(config)

# Calling the add_node function we create a network node that
# will run the CounterProtocol we created.
for _ in range(10):
    builder.add_node(CounterProtocol, (0, 0, 0))

# Handlers enable certain simulation features. In the case of our
# simulation all we really need is a timer.
builder.add_handler(TimerHandler())
builder.add_handler(CommunicationHandler())

simulation = builder.build()
simulation.start_simulation()

