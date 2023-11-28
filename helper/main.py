from code_generator import CodeGenerator
from generate_simulation import AlphabetMatrix


if __name__ == "__main__":
    matrix = AlphabetMatrix(5, 5)
    matrix.place_letter("A")
    matrix.scale_matrix(10)
    coords = matrix.get_coordinates_list()

    code_generator = CodeGenerator(
        # ground_coord=(0, 0, 0),
        sensor_coords=coords,
        mobile_coords=coords,
        # protocol_ground="ZigZagProtocolGround",
        protocol_sensor="ZigZagProtocolSensor",
        protocol_mobile="ZigZagProtocolMobile",
    )
    
    code_generator.generate_python_file()

    code_generator.generate_mission_file()
