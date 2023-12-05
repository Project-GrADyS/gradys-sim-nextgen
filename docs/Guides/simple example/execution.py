from gradysim.simulator.handler.communication import CommunicationHandler
from gradysim.simulator.handler.mobility import MobilityHandler
from gradysim.simulator.handler.timer import TimerHandler
from gradysim.simulator.handler.visualization import VisualizationHandler, VisualizationConfiguration
from gradysim.simulator.simulation import SimulationBuilder, SimulationConfiguration
from protocol import SimpleSensorProtocol, SimpleGroundStationProtocol, SimpleUAVProtocol

if __name__ == '__main__':
    config = SimulationConfiguration(
        duration=100
    )
    builder = SimulationBuilder(config)

    builder.add_node(SimpleSensorProtocol, (150, 0, 0))
    builder.add_node(SimpleSensorProtocol, (0, 150, 0))
    builder.add_node(SimpleSensorProtocol, (-150, 0, 0))
    builder.add_node(SimpleSensorProtocol, (0, -150, 0))

    builder.add_node(SimpleUAVProtocol, (0, 0, 0))
    builder.add_node(SimpleUAVProtocol, (0, 0, 0))
    builder.add_node(SimpleUAVProtocol, (0, 0, 0))
    builder.add_node(SimpleUAVProtocol, (0, 0, 0))

    builder.add_node(SimpleGroundStationProtocol, (0, 0, 0))

    builder.add_handler(TimerHandler())
    builder.add_handler(CommunicationHandler())
    builder.add_handler(MobilityHandler())
    builder.add_handler(VisualizationHandler(VisualizationConfiguration(
        x_range=(-150, 150),
        y_range=(-150, 150),
        z_range=(0, 150)
    )))

    simulation = builder.build()
    simulation.start_simulation()
