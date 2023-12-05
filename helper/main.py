from code_generator import CodeGenerator

if __name__ == "__main__":

    code_generator = CodeGenerator(
        protocol_location =  "/home/lac/Documents/Gradys/workspace/gradys-sim-prototype/showcases",

        protocol="zigzag",
        
        protocol_ground="ZigZagProtocolSensor",
        protocol_sensor="ZigZagProtocolSensor",
        protocol_mobile="ZigZagProtocolMobile",
        
        protocol_ground_filename="protocol_sensor",
        protocol_sensor_filename="protocol_sensor",
        protocol_mobile_filename="protocol_mobile",

        pattern = 'A',
        pattern_scale = 3
    )
    
    code_generator.generate_ini_file()
    code_generator.generate_python_file()
    code_generator.generate_mission_file()
