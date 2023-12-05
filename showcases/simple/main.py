from gradysim.simulator.handler.communication import CommunicationHandler, CommunicationMedium
from gradysim.simulator.handler.mobility import MobilityHandler
from gradysim.simulator.handler.timer import TimerHandler
from gradysim.simulator.handler.visualization import VisualizationHandler
from gradysim.simulator.simulation import SimulationBuilder, SimulationConfiguration
from protocol_sensor import SimpleProtocolSensor
from protocol_mobile import SimpleProtocolMobile
from protocol_ground import SimpleProtocolGround


def run_simulation(real_time: bool):
    builder = SimulationBuilder(SimulationConfiguration(duration=180, debug=True, real_time=real_time))
    builder.add_handler(CommunicationHandler(CommunicationMedium(transmission_range=50)))
    builder.add_handler(TimerHandler())
    builder.add_handler(MobilityHandler())

    if real_time:
        builder.add_handler(VisualizationHandler())

    # Ground location
    builder.add_node(SimpleProtocolGround, (-6.9, 0.0, 0.0))
    
    # Drone locations 
    builder.add_node(SimpleProtocolMobile, (-6.9, 0.0, 0.0))
    builder.add_node(SimpleProtocolMobile, (-3.9000000000000004, -3.0, 0.0))
    builder.add_node(SimpleProtocolMobile, (-3.9000000000000004, 3.0, 0.0))
    builder.add_node(SimpleProtocolMobile, (-0.9000000000000004, -6.0, 0.0))
    
    # Sensor locations 
    builder.add_node(SimpleProtocolSensor, (-3.9000000000000004, -3.0, 0.0))
    builder.add_node(SimpleProtocolSensor, (-3.9000000000000004, 3.0, 0.0))
    builder.add_node(SimpleProtocolSensor, (-0.9000000000000004, -6.0, 0.0))
    builder.add_node(SimpleProtocolSensor, (-0.9000000000000004, 6.0, 0.0))
    
    # Simulation
    simulation = builder.build()
    simulation.start_simulation()


if __name__ == '__main__':
    run_simulation(True)
