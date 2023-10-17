from docs.counter_protocol import CounterProtocol
from simulator.node.handler.timer import TimerHandler
from simulator.simulation import SimulationBuilder, SimulationConfiguration

config = SimulationConfiguration(
    duration=10
)
builder = SimulationBuilder(config)
builder.add_node(CounterProtocol, (0, 0, 0))

builder.add_handler(TimerHandler())

simulation = builder.build()
simulation.start_simulation()

