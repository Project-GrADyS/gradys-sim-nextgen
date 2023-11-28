import os
from typing import Optional

import numpy as np
from jinja2 import Environment, FileSystemLoader

from gradysim.protocol.position import Position


class CodeGenerator:
    def __init__(
        self,
        ground_coord: Optional[Position] = None,
        sensor_coords: Optional[list[Position]] = None,
        mobile_coords: Optional[list[Position]] = None,
        protocol_ground: Optional[str] = None,
        protocol_sensor: Optional[str] = None,
        protocol_mobile: Optional[str] = None,
        duration: int = 180,
        debug: bool = True,
        transmission_range: int = 50,
    ) -> None:
        self.ground_coord: Position = ground_coord
        self.sensor_coords: list[Position] = sensor_coords
        self.mobile_coords: list[Position] = mobile_coords

        self.protocol_ground: str = protocol_ground
        self.protocol_sensor: str = protocol_sensor
        self.protocol_mobile: str = protocol_mobile

        self.duration: int = duration
        self.debug: bool = debug
        self.transmission_range: int = transmission_range

        self.env = Environment(loader=FileSystemLoader(os.getcwd()))

    def add_line(self, line):
        self.code += line + "\n"

    def generate_python_code(self):
        template = self.env.get_template("python_template.jinja")

        data = {
            "ground_coord": self.ground_coord,
            "mobile_coords": self.mobile_coords,
            "sensor_coords": self.sensor_coords,
            "protocol_ground": self.protocol_ground,
            "protocol_sensor": self.protocol_sensor,
            "protocol_mobile": self.protocol_mobile,
            "duration": self.duration,
            "debug": self.debug,
            "transmission_range": self.transmission_range,
        }

        generated_code = template.render(data)
        print(generated_code)

    def generate_ini_file(self, sections):
        
        def get_long_lat(x=None, y=None, z=None):
            R = 6371
            lat = np.degrees(np.arcsin(z / R))
            lon = np.degrees(np.arctan2(y, x))
            return lat, lon
        
        lat, lon = get_long_lat(x, y, z)

        template = self.env.get_template("ini_template.jinja")

        data = {
            "ground_coord": self.ground_coord,
            "mobile_coords": self.mobile_coords,
            "sensor_coords": self.sensor_coords,
            "protocol_ground": self.protocol_ground,
            "protocol_sensor": self.protocol_sensor,
            "protocol_mobile": self.protocol_mobile,
            "duration": self.duration,
            "debug": self.debug,
            "transmission_range": self.transmission_range,
        }

        generated_code = template.render(data)
        print(generated_code)






def get_cartesian(lat=None, lon=None):
    lat, lon = np.deg2rad(lat), np.deg2rad(lon)
    R = 6371  # radius of the earth
    x = R * np.cos(lat) * np.cos(lon)
    y = R * np.cos(lat) * np.sin(lon)
    z = R * np.sin(lat)
    return x, y, z

x, y, z = get_cartesian(-15.840068, -47.926633)
