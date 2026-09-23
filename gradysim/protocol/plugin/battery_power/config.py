"""
Configuration dataclass for the Battery Power Plugin
"""

from dataclasses import dataclass

@dataclass
class BatteryPowerConfiguration:
    """
    Configuration parameters for BatteryPowerPlugin
    """
    battery_initial_charge: float = 1.0
    """Initial battery charge, 0 means no energy while 1.0 is fully charged."""

    battery_capacity: float = 5000.0
    """Battery capacity in milliampere-hours (mAh)."""

    battery_voltage: float = 14.0
    """Battery voltage in Volts (V)."""

    battery_charge_constant: float = 0.01
    """Simplified constant to simulate how long it takes to charge the battery.
    The charged energy is calculated as: `charged_energy = battery_charge_constant * charge_time`."""

    battery_efficiency: float = 0.6
    """Battery efficiency as a decimal (0 to 1)."""

    external_power_load: float = 0.0
    """External power source (in Watts) that can be used in the UAV, like companion computers"""

    total_uav_mass: float = 2.0
    """Total mass of the UAV in kilograms (kg), including battery and payload.
    Default reflects a loaded Holybro X500 V2 (frame + electronics + 4S ~5000mAh battery + payload)."""

    power_efficiency: float = 0.8
    """Power efficiency of the UAV's propulsion system as a decimal (0 to 1)."""

    X_drag_coefficient: float = 0.8
    """Drag coefficient in the X direction """

    Z_drag_coefficient: float = 0.8
    """Drag coefficient in the z direction """

    X_ref_area: float = 0.015
    """Reference area in the X direction (m^2)"""

    Z_ref_area: float = 0.0335
    """Reference area in the z direction (m^2)"""

    air_density: float = 1.225
    """Air density in kg/m^3 (default is at sea level)"""

    gravity: float = 9.81
    """Gravitational acceleration in m/s^2"""

    propeller_radius: float = 0.127
    """Radius of the propeller in meters (m)"""

    number_of_rotors: int = 4
    """Number of rotors in the UAV"""




