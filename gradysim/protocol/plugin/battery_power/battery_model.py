"""
Power model for the battery consumption of the UAV.
The model is based on the following paper:
    Energy-Aware Multi-Agent Reinforcement Learning
    for Collaborative Execution in Mission-Oriented
    Drone Networks

Velocity convention: drone_speed = (vx, vz) in the body frame.
    vx > 0 : forward
    vz > 0 : upwards (climb)
Lateral (y) motion is not modelled.
"""

import numpy as np
from typing import Optional

class BatteryPowerModel:
    """
    A simple battery power model for a UAV.
    The model assumes that the UAV is powered by a battery and that the battery has a finite capacity.
    The model also assumes that the UAV consumes power depending on the theory of rotor dynamics.
    It is also assuming that the UAV moves always in the x body frame in the horizontal movement.
    """

    def __init__(self, mass: float = 1.5, payload: float = 0.0, power_efficiency: float = 0.6,
                 battery_efficiency: float = 0.6,
                 external_power: float = 0.0, battery_charging_constant: float = 0.01,
                 battery_capacity: float = 5000.0, battery_voltage: float = 14.0,
                 battery_initial_charge: float = 1.0,
                 X_ref_area: float = 0.015, Z_ref_area: float = 0.0335,
                 X_drag_coef: float = 0.8, Z_drag_coef: float = 0.8,
                 air_density: float = 1.225, gravity: float = 9.81, propeller_radius: float = 0.127,
                 number_of_rotors: int = 4, time_step: float = 1.0,
                 random_air_speed: bool = False, random_air_speed_u: Optional[float] = None, 
                 random_air_speed_sigma: Optional[float] = None):
        self.mass = mass
        self.payload = payload
        self.external_power = external_power
        self.POWER_EFFICIENCY = power_efficiency
        self.BATTERY_EFFICIENCY = battery_efficiency
        self.BATTERY_CHARGING_CONSTANT = battery_charging_constant
        self.BATTERY_VOLTAGE = battery_voltage
        self.BATTERY_CAPACITY_ENERGY = battery_capacity * battery_voltage * 3.6  # in Joules
        self.battery_current_energy = self.BATTERY_CAPACITY_ENERGY
        self.X_REF_AREA = X_ref_area
        self.Z_REF_AREA = Z_ref_area
        self.X_DRAG_COEF = X_drag_coef
        self.Z_DRAG_COEF = Z_drag_coef
        self.AIR_DENSITY = air_density
        self.GRAVITY = gravity
        self.PROP_RADIUS = propeller_radius
        self.N_ROTORS = number_of_rotors
        self.DISK_AREA = self.N_ROTORS * np.pi * (self.PROP_RADIUS ** 2)
        self.battery_status = battery_initial_charge  # fraction, 0 to 1
        self.TIME_STEP = time_step  # seconds
        self.air_speed = 0.0 # the velocity is calculated relatively to the air speed
        self.RANDOM_AIR_SPEED = random_air_speed

        if self.RANDOM_AIR_SPEED == True:
            if random_air_speed_u is None or random_air_speed_sigma is None:
                raise RuntimeError("Must provide the mean and std deviation terms")
            else:
                self.random_air_speed_u = random_air_speed_u
                self.random_air_speed_sigma = random_air_speed_sigma
            

    @property
    def weight(self) -> float:
        """Total weight in Newtons."""
        return (self.mass + self.payload) * self.GRAVITY

    def drag_resistance(self, drone_speed: tuple[float, float]) -> tuple[float, float]:
        """From the 2D velocity vector (vx, vz) in the body frame, calculate the air
        resistance along each axis."""
        vx, vz = drone_speed
        drag_x = 0.5 * self.AIR_DENSITY * self.X_DRAG_COEF * self.X_REF_AREA * vx **2 
        drag_z = 0.5 * self.AIR_DENSITY * self.Z_DRAG_COEF * self.Z_REF_AREA * vz **2 
        return (drag_x, drag_z)

    def get_thrust_components(self, drone_speed: tuple[float, float]) -> tuple[float, float]:
        """Steady-state thrust components (thrust_x, thrust_z) in Newtons.
        Horizontally the tilted disk supplies the drag; vertically it supplies the
        weight plus the vertical drag."""
        drag_x, drag_z = self.drag_resistance(drone_speed)
        return (drag_x, self.weight + drag_z)

    def get_inclination_angle(self, drone_speed: tuple[float, float]) -> float:
        """Calculate the inclination angle of the UAV, in radians, from its speed and
        drag forces: tan(theta) = thrust_x / thrust_z."""
        thrust_x, thrust_z = self.get_thrust_components(drone_speed)
        return np.arctan2(thrust_x, thrust_z)

    def get_total_trust(self, drone_speed: tuple[float, float]) -> float:
        """Calculate the total thrust required to maintain the UAV's speed and altitude."""
        thrust_x, thrust_z = self.get_thrust_components(drone_speed)
        return np.sqrt(thrust_x**2 + thrust_z**2)

    def calculate_motors_power_consumption(self, drone_speed: tuple[float, float],
                                           air_speed: Optional[float] = None) -> float:
        """Calculate the power consumption of the UAV based on its speed and drag forces.

        air_speed, when given, is used as the random air speed of this step instead of
        drawing one from np.random. It lets the caller own the random stream."""
        vx, vz = drone_speed

        if self.RANDOM_AIR_SPEED == True:
            if air_speed is None:
                air_speed = np.random.normal(self.random_air_speed_u, self.random_air_speed_sigma)
            self.air_speed = air_speed
            vx = vx - self.air_speed

        drone_speed = (vx, vz)

        thrust_x, thrust_z = self.get_thrust_components(drone_speed)

        trust = self.get_total_trust(drone_speed)

        # Air speed in hover
        v_h = np.sqrt(trust / (2 * self.AIR_DENSITY * self.DISK_AREA))

        # Induced Velocity in Forward Flight (Glauert approximation)
        v_i = trust / (2 * self.AIR_DENSITY * self.DISK_AREA * np.sqrt(vx ** 2 + vz ** 2 + v_h ** 2))

        # Induced Power
        induced_power = trust * v_i

        # Parasite Power
        parasite_power = thrust_x * abs(vx)

        # Vertical movement power: weight plus vertical drag, times climb rate.
        if vz > 0:
            climb_power = thrust_z * vz
        else:
            climb_power = 0.0

        return (induced_power + parasite_power + climb_power) / self.POWER_EFFICIENCY

    def get_power_consumption(self, drone_speed: tuple[float, float],
                              air_speed: Optional[float] = None) -> float:
        """Calculate the total power drawn from the battery pack, including losses from
        battery internal resistance/inefficiency (BATTERY_EFFICIENCY)."""
        motor_consumption = self.calculate_motors_power_consumption(drone_speed, air_speed)
        return (motor_consumption + self.external_power) / self.BATTERY_EFFICIENCY

    def update_external_power(self, external_power: float):
        """Update the external power consumption of the UAV."""
        self.external_power = external_power

    def get_energy_consumed(self, power_consumption: float, time_interval: float) -> float:
        """Calculate the energy consumed by the UAV over a given time interval."""
        energy_consumed = power_consumption * time_interval
        return energy_consumed

    def get_current_battery_energy(self) -> float:
        """Get the current battery energy in Joules."""
        return self.battery_current_energy

    def get_battery_status(self) -> float:
        """Get the current battery status as a percentage (0 to 1)."""
        return self.battery_status

    def update_battery_status(self):
        """Update the battery status based on the current battery energy."""
        self.battery_status = self.battery_current_energy / self.BATTERY_CAPACITY_ENERGY

    def charge_battery(self, time_interval: float):
        """Charge the battery over a given time interval."""
        charged_energy = self.BATTERY_CHARGING_CONSTANT * time_interval
        self.battery_current_energy += charged_energy
        self.battery_current_energy = min(self.battery_current_energy, self.BATTERY_CAPACITY_ENERGY)
        self.update_battery_status()

    def charge_battery_to_full(self):
        """Charge the battery to full capacity."""
        self.battery_current_energy = self.BATTERY_CAPACITY_ENERGY
        self.update_battery_status()

    def add_payload(self, additional_payload: float):
        """Add additional payload to the UAV, affecting its weight and power consumption."""
        self.payload += additional_payload

    def remove_payload(self, removed_payload: float):
        """Remove payload from the UAV, affecting its weight and power consumption."""
        self.payload = max(0.0, self.payload - removed_payload)

    def manage_battery_during_flight(self, drone_speed: tuple[float, float],
                                     air_speed: Optional[float] = None):
        """Manage the battery during flight by calculating power consumption and updating battery status."""
        power_consumption = self.get_power_consumption(drone_speed, air_speed)
        energy_consumed = self.get_energy_consumed(power_consumption, self.TIME_STEP)
        self.battery_current_energy -= energy_consumed
        if self.battery_current_energy < 0:
            self.battery_current_energy = 0
            self.update_battery_status()
            raise RuntimeError("Battery depleted during flight.")
        self.update_battery_status()

    def change_battery_efficiency(self, new_battery_efficiency: float):
        """ This can happen because some regions are much hotter than others for instance or you want to simulate
        some battery degradation during the flight"""
        self.POWER_EFFICIENCY = new_battery_efficiency 

    
