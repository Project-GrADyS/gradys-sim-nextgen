from code_generator import CodeGenerator


if __name__ == "__main__":
    """
    This helper allows to generate the main.py, ini file as well as the mission file for running the same experiements
    both in Python and Omnet++ without a big hassle. One simply has to define the location of the protocol location, protocol
    names and how the files are names. Afterwards one can select of of many patterns that distribute the drones, sensors and
    the groundstation in a certain patten. Those patterns are very easily to extend if one does not want to use the existing
    patterns.
    """
    code_generator = CodeGenerator(
        protocol_location="/home/lac/Documents/Gradys/workspace/gradys-sim-prototype/showcases",
        protocol="zigzag",
        protocol_ground="ZigZagProtocolSensor",
        protocol_sensor="ZigZagProtocolSensor",
        protocol_mobile="ZigZagProtocolMobile",
        protocol_ground_filename="protocol_sensor",
        protocol_sensor_filename="protocol_sensor",
        protocol_mobile_filename="protocol_mobile",
        pattern="Test",
        pattern_scale=3,
    )

    # # This is another example how the code generator can be used for another protocol
    # code_generator = CodeGenerator(
    #     protocol_location =  "/home/lac/Documents/Gradys/workspace/gradys-sim-prototype/showcases",

    #     protocol="simple",

    #     protocol_ground="SimpleProtocolGround",
    #     protocol_sensor="SimpleProtocolSensor",
    #     protocol_mobile="SimpleProtocolMobile",

    #     protocol_ground_filename="protocol_ground",
    #     protocol_sensor_filename="protocol_sensor",
    #     protocol_mobile_filename="protocol_mobile",

    #     pattern = 'Test',
    #     pattern_scale = 3
    # )

    code_generator.generate_ini_file()
    code_generator.generate_python_file()
    code_generator.generate_mission_file()
