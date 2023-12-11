import os
from typing import Optional

from jinja2 import Environment, FileSystemLoader

from gradysim.protocol.position import Position
from generate_simulation import AlphabetMatrix


class CodeGenerator:
    def __init__(
        self,
        # Required fields
        protocol_location,
        protocol,
        protocol_ground,
        protocol_sensor,
        protocol_mobile,
        protocol_ground_filename,
        protocol_sensor_filename,
        protocol_mobile_filename,
        # Optional fields
        pattern: Optional[str] = None,
        pattern_scale: Optional[int] = None,
        ground_coord: Optional[Position] = None,
        sensor_coords: Optional[list[Position]] = None,
        mobile_coords: Optional[list[Position]] = None,
        scene_longitude=-47.926634,
        scene_latitude=-15.840075,
        duration: int = 180,
        debug: bool = True,
        transmission_range: int = 50,
    ) -> None:
        self.protocol_location: str = protocol_location
        self.protocol: str = protocol
        self.protocol_ground: str = protocol_ground
        self.protocol_sensor: str = protocol_sensor
        self.protocol_mobile: str = protocol_mobile
        self.protocol_ground_filename: str = protocol_ground_filename
        self.protocol_sensor_filename: str = protocol_sensor_filename
        self.protocol_mobile_filename: str = protocol_mobile_filename

        assert (
            bool(pattern)
            and bool(pattern_scale)
            and not bool(ground_coord)
            and not bool(sensor_coords)
            and not bool(mobile_coords)
        ) or (
            not bool(pattern)
            and not bool(pattern_scale)
            and bool(ground_coord)
            and bool(sensor_coords)
            and bool(mobile_coords)
        ), "Assertion failed: Either provie pattern and pattern_scale or coords for ground, sensors and mobile"

        if pattern and pattern_scale:
            self.pattern: str = pattern
            self.pattern_scale: int = pattern_scale

            # Generate coordinates based on defined patern and scale
            matrix = AlphabetMatrix(5, 5)
            matrix.place_letter(self.pattern)
            matrix.scale_matrix(self.pattern_scale)

            # Generate coords, select first point as ground station
            coords = matrix.get_coordinates_list()

            self.ground_coord: Position = coords[0]
            self.sensor_coords: list[Position] = coords[1:]
            self.mobile_coords: list[Position] = coords

        else:
            self.ground_coord: Position = ground_coord
            self.sensor_coords: list[Position] = sensor_coords
            self.mobile_coords: list[Position] = mobile_coords

        self.scene_longitude = scene_longitude
        self.scene_latitude = scene_latitude
        self.duration: int = duration
        self.debug: bool = debug
        self.transmission_range: int = transmission_range

        self.env = Environment(loader=FileSystemLoader(os.getcwd()))

    def generate_python_file(self):
        print("Python main file (filename: main.py) \n")

        template = self.env.get_template("python_template.jinja")

        data = {
            "ground_coord": self.ground_coord,
            "mobile_coords": self.mobile_coords,
            "sensor_coords": self.sensor_coords,
            "protocol_ground": self.protocol_ground,
            "protocol_sensor": self.protocol_sensor,
            "protocol_mobile": self.protocol_mobile,
            "protocol_ground_filename": self.protocol_ground_filename,
            "protocol_sensor_filename": self.protocol_sensor_filename,
            "protocol_mobile_filename": self.protocol_mobile_filename,
            "duration": self.duration,
            "debug": self.debug,
            "transmission_range": self.transmission_range,
        }

        generated_code = template.render(data)

        print(generated_code + "\n")

    def generate_mission_file(self):
        print("Mission file (filename: mission.txt) \n")

        if self.ground_coord:
            print(
                f"{self.ground_coord[0]},{self.ground_coord[1]},{self.ground_coord[2]}"
            )

        for sensor_coord in self.sensor_coords:
            print(f"{sensor_coord[0]},{sensor_coord[1]},{sensor_coord[2]}")

        print("\n")


    def generate_ini_file(self):
        transformed_mobile_coords_to_lat_long = []
        for idx, coord in enumerate(self.mobile_coords):
            transformed_mobile_coords_to_lat_long.append((idx, coord[0], coord[1], coord[2]))

        transformed_sensor_coords_to_lat_long = []
        for idx, coord in enumerate(self.sensor_coords):
            transformed_sensor_coords_to_lat_long.append((idx, coord[0], coord[1], coord[2]))

        template = self.env.get_template("ini_template.jinja")

        data = {
            # Scene orientation and groundstation
            "scene_longitude": self.scene_longitude,
            "scene_latitude": self.scene_latitude,
            "protocol_location": self.protocol_location,
            "protocol": self.protocol,
            "protocol_ground_filename": self.protocol_ground_filename,
            "protocol_sensor_filename": self.protocol_sensor_filename,
            "protocol_mobile_filename": self.protocol_mobile_filename,
            "protocol_ground": self.protocol_ground,
            "protocol_sensor": self.protocol_sensor,
            "protocol_mobile": self.protocol_mobile,
            "ground_information": (
                0,
                self.ground_coord[0],
                self.ground_coord[1],
                self.ground_coord[2],
            ),
            "sensor_information": transformed_sensor_coords_to_lat_long,
            "mobile_information": transformed_mobile_coords_to_lat_long,
            "sensor_amount": len(transformed_sensor_coords_to_lat_long),
            "mobile_amount": len(transformed_mobile_coords_to_lat_long),
        }

        generated_code = template.render(data)

        print(generated_code)


# P = pyproj.Proj(proj='utm', zone=22, ellps='WGS84', preserve_units=True)

# def LonLat_To_XY(Lon, Lat):
#     return P(Lon, Lat)

# def XY_To_LonLat(x,y):
#     return P(x, y, inverse=True)

# print("Ini file (filename: omnetpp.ini) \n")

# # Transform coords to longitude and latitude
# x, y = LonLat_To_XY(self.scene_longitude, self.scene_latitude)

# ground_pos = (x+self.ground_coord[0], y + self.ground_coord[1], 0)
# ground_lon, ground_lat = XY_To_LonLat(ground_pos[0], ground_pos[1])
# transformed_ground_coords_to_lat_long = (0, ground_lon, ground_lat)

# transformed_mobile_coords_to_lat_long = []
# for idx, coord in enumerate(self.mobile_coords):
#     pos = (x+coord[0], y + coord[1], 0)
#     lon, lat = XY_To_LonLat(pos[0], pos[1])
#     transformed_mobile_coords_to_lat_long.append((idx, coord[0], coord[1], coord[2]))

# transformed_sensor_coords_to_lat_long = []
# for idx, coord in enumerate(self.sensor_coords):
#     pos = (x+coord[0], y + coord[1], 0)
#     lon, lat = XY_To_LonLat(pos[0], pos[1])
#     transformed_sensor_coords_to_lat_long.append((idx, coord[0], coord[1], coord[2]))