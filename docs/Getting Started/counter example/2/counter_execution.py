from counter_protocol import CounterProtocol
from gradysim.simulator import CommunicationHandler
from gradysim.simulator import TimerHandler
from gradysim.simulator.simulation import SimulationBuilder, SimulationConfiguration

# Configuring the simulator. The only option that interests us
# is limiting the simulator to 10 real-world seconds.
config = SimulationConfiguration(
    duration=10
)
# Instantiating the simulator builder with the created config
builder = SimulationBuilder(config)

# Calling the add_node function we create a network node that
# will run the CounterProtocol we created.
for _ in range(10):
    builder.add_node(CounterProtocol, (0, 0, 0))

# Handlers enable certain simulator features. In the case of our
# simulator all we really need is a timer.
builder.add_handler(TimerHandler())
builder.add_handler(CommunicationHandler())

simulation = builder.build()
simulation.start_simulation()

