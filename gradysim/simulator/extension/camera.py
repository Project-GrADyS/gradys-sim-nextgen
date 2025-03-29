import math
from dataclasses import dataclass
from typing import Optional, TypedDict, Tuple, List

from gradysim.protocol.interface import IProtocol
from gradysim.protocol.position import Position
from gradysim.simulator.extension.extension import Extension
from gradysim.simulator.handler.mobility import MobilityHandler

class DetectedNode(TypedDict):
    position: Position
    type: str

@dataclass
class CameraConfiguration:
    """
    Configuration class for the camera hardware
    """

    camera_reach: float
    """The length of the cone that represents the camera's area of detection"""

    camera_theta: float
    """The angle that determines how wide the cone, that represents the camera's area of detection, is"""

    facing_elevation: float
    """The inclination of where the camera is pointing to in degrees, with 0 being directly up"""

    facing_rotation: float
    """The rotation of the camera in degrees, with zero being along the x-axis in the positive direction"""

class CameraHardware(Extension):
    """
    This extension simulates a camera hardware that can detect other nodes within its area of detection. The camera
    has a reach, field of view, and direction of facing. The camera is capable of taking pictures, returning the list
    of detected nodes within its area of detection.

    The area of detection is a cone whose point is at the node's position and base faces the direction the camera is
    pointing to, determined by the facing_inclination and facing_rotation attributes of the configuration. The cone's
    angle at the point is determined by the field_of_view attribute of the configuration. The cone's length, or the
    distance between its point and base, is determined by the cone_reach attribute of the configuration.
    """

    def __init__(self, protocol: IProtocol, configuration: CameraConfiguration):
        super().__init__(protocol)
        if self._provider is not None:
            self._mobility: Optional[MobilityHandler] = self._provider.handlers.get('mobility')
        self._configuration = configuration

        self._camera_vector = self._camera_direction_unit_vector()
        self._camera_theta = math.radians(self._configuration.camera_theta)

    def _camera_direction_unit_vector(self) -> Tuple[float, float, float]:
        """
        Returns the unit vector that represents the direction the camera is facing to
        Returns:
            A tuple representing the unit vector
        """
        facing_inclination = math.radians(self._configuration.facing_elevation)
        facing_rotation = math.radians(self._configuration.facing_rotation)

        x = math.sin(facing_inclination) * math.cos(facing_rotation)
        y = math.sin(facing_inclination) * math.sin(facing_rotation)
        z = math.cos(facing_inclination)

        return x, y, z

    def take_picture(self) -> List[DetectedNode]:
        """
        This simulated camera hardware is able to detect other nodes within its are of detection. This method returns
        the list of nodes currently inside the area of detection of the camera.
        Returns:
            A list of detected nodes
        """
        if self._mobility is None:
            return []

        node_position = self._provider.node.position

        other_nodes = [node for node in self._mobility.nodes.values() if node.id != self._provider.node.id]

        detected_nodes = []
        for node in other_nodes:
            other_node_position = node.position
            relative_vector = (
                other_node_position[0] - node_position[0],
                other_node_position[1] - node_position[1],
                other_node_position[2] - node_position[2]
            )

            # Check if the node is within the camera's reach
            distance = math.sqrt(relative_vector[0] ** 2 + relative_vector[1] ** 2 + relative_vector[2] ** 2)
            if distance > self._configuration.camera_reach:
                continue

            if distance > 0:
                # Check if the angle between vectors is less than theta
                normalized_relative_vector = (
                    relative_vector[0] / distance,
                    relative_vector[1] / distance,
                    relative_vector[2] / distance
                )
                dot_product = (
                    self._camera_vector[0] * normalized_relative_vector[0] +
                    self._camera_vector[1] * normalized_relative_vector[1] +
                    self._camera_vector[2] * normalized_relative_vector[2]
                )
                angle = math.acos(dot_product) - 1e-6 # Tolerance
                if angle > self._camera_theta:
                    continue

            detected_nodes.append({
                'position': other_node_position,
                'type': 'node'
            })

        return detected_nodes

    def change_facing(self, facing_elevation: float, facing_rotation: float):
        """
        Changes the direction the camera is facing to
        Args:
            facing_elevation: The inclination of where the camera is pointing to in degrees, with 0 being at the ground
            facing_rotation: The rotation of the camera in degrees, with zero being along the x-axis in the positive direction
        """
        self._configuration.facing_elevation = facing_elevation
        self._configuration.facing_rotation = facing_rotation
        self._camera_vector = self._camera_direction_unit_vector()