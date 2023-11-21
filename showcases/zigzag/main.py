from gradysim.simulator.handler.communication import CommunicationHandler, CommunicationMedium
from gradysim.simulator.handler.mobility import MobilityHandler
from gradysim.simulator.handler.timer import TimerHandler
from gradysim.simulator.handler.visualization import VisualizationHandler
from gradysim.simulator.simulation import SimulationBuilder, SimulationConfiguration, PositionScheme
from protocol_sensor import ZigZagProtocolSensor
from protocol_mobile import ZigZagProtocolMobile


def run_simulation(real_time: bool):
    builder = SimulationBuilder(SimulationConfiguration(duration=180, debug=True, real_time=real_time))
    builder.add_handler(CommunicationHandler(CommunicationMedium(transmission_range=20)))
    builder.add_handler(TimerHandler())
    builder.add_handler(MobilityHandler())

    if real_time:
        builder.add_handler(VisualizationHandler())

    builder.add_node(ZigZagProtocolMobile, (0, 0, 0))
    builder.add_node(ZigZagProtocolMobile, (20, 20, 0))

    for _ in range(1):
        builder.add_node(ZigZagProtocolSensor, PositionScheme.random((-5, 5), (-5, 5), (0, 5)))

    simulation = builder.build()
    simulation.start_simulation()


if __name__ == '__main__':
    run_simulation(True)
