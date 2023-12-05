from gradysim.simulator.handler.communication import CommunicationHandler, CommunicationMedium
from gradysim.simulator.handler.mobility import MobilityHandler
from gradysim.simulator.handler.timer import TimerHandler
from gradysim.simulator.handler.visualization import VisualizationHandler
from gradysim.simulator.simulation import SimulationBuilder, SimulationConfiguration
from protocol_sensor import ZigZagProtocolSensor
from protocol_mobile import ZigZagProtocolMobile


def run_simulation(real_time: bool):
    builder = SimulationBuilder(SimulationConfiguration(duration=10, debug=True, real_time=real_time))
    builder.add_handler(CommunicationHandler(CommunicationMedium(transmission_range=50)))
    builder.add_handler(TimerHandler())
    builder.add_handler(MobilityHandler())

    if real_time:
        builder.add_handler(VisualizationHandler())

    builder.add_node(ZigZagProtocolSensor, (-5.0, -5.0, 0.0))
    
    # Drone locations 
    builder.add_node(ZigZagProtocolMobile, (-5.0, -5.0, 0.0))
    builder.add_node(ZigZagProtocolMobile, (1.0, 1.0, 0.0))
    builder.add_node(ZigZagProtocolMobile, (4.0, 4.0, 0.0))
    
    # Sensor locations 
    builder.add_node(ZigZagProtocolSensor, (1.0, 1.0, 0.0))
    builder.add_node(ZigZagProtocolSensor, (4.0, 4.0, 0.0))
    
    # Simulation
    simulation = builder.build()
    simulation.start_simulation()


if __name__ == '__main__':
    run_simulation(True)
