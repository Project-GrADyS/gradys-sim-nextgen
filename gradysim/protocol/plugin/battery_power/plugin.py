"""
This module declares a plugin that lets a protocol estimate the energy consumption and the battery status of a UAV
based on its speed and drag forces. 

Beware that this plugin needs to receive the Dynamic Velocity Mobility Telemetry, because the model is based on the UAV velocity. 
"""

import logging
from typing import Tuple

import numpy as np

from gradysim.protocol.interface import IProtocol
from gradysim.protocol.plugin.dispatcher import create_dispatcher, DispatchReturn
from gradysim.protocol.messages.telemetry import Telemetry
from gradysim.simulator.handler.mobility.dynamic_velocity.telemetry import DynamicVelocityTelemetry

from .config import BatteryPowerConfiguration
from .battery_model import BatteryPowerModel

CONTROL_TIMER_TAG = "BatteryPowerPlugin__control_timer"
"""The plugin drives its loop using a timer with this name, make sure it doesn't
conflict with other timers your protocol schedules."""

class BatteryPowerPluginException(Exception):
    pass

class BatteryPowerPlugin:
    """
    Use this plugin if you want your node to estimate the energy consumption and the battery status of a UAV
    based on its speed and drag forces. 

    This plugin requires the node's mobility to be provided by Dynamic Velocity Mobility Handler.
    """

    def __init__(self, protocol: IProtocol, configuration: BatteryPowerConfiguration):

        self._dispatcher = create_dispatcher(protocol)
        self._protocol = protocol
        self._config = configuration
        self._logger = logging.getLogger()

        self._battery_model = BatteryPowerModel(
            mass=configuration.total_uav_mass,
            power_efficiency=configuration.power_efficiency,
            battery_efficiency=configuration.battery_efficiency,
            external_power=configuration.external_power_load,
            battery_charging_constant=configuration.battery_charge_constant,
            battery_capacity=configuration.battery_capacity,
            battery_voltage=configuration.battery_voltage,
            battery_initial_charge=configuration.battery_initial_charge,
            X_ref_area=configuration.X_ref_area,
            Z_ref_area=configuration.Z_ref_area,
            X_drag_coef=configuration.X_drag_coefficient,
            Z_drag_coef=configuration.Z_drag_coefficient,
            air_density=configuration.air_density,
            gravity=configuration.gravity,
            propeller_radius=configuration.propeller_radius,
            number_of_rotors=configuration.number_of_rotors,
            time_step=1.0,
        )
        self.velocity = [0.0, 0.0]  # Initialize velocity to zero
        self._initialize_telemetry_handling()
        self._initialize_battery_loop()

    def _initialize_telemetry_handling(self):
        def telemetry_handler(_instance: IProtocol, telemetry: Telemetry) -> DispatchReturn:
            if not isinstance(telemetry, DynamicVelocityTelemetry):
                raise BatteryPowerPluginException(
                    "BatteryPowerPlugin requires DynamicVelocityTelemetry, which is only emitted "
                    "by DynamicVelocityMobilityHandler. Make sure your simulation uses that "
                    "mobility handler."
                )
        
            self.velocity = [telemetry.current_velocity[0], telemetry.current_velocity[2]]
            return DispatchReturn.CONTINUE
        
        self._dispatcher.register_handle_telemetry(telemetry_handler)

    def _initialize_battery_loop(self) -> None:
            """Drives the periodic battery management model."""

            def timer_handler(_instance: IProtocol, timer: str) -> DispatchReturn:
                if timer != CONTROL_TIMER_TAG:
                    return DispatchReturn.CONTINUE

                self.battery_step()
                self._schedule_next_tick()

                return DispatchReturn.INTERRUPT

            self._dispatcher.register_handle_timer(timer_handler)
            self._schedule_next_tick()

    def _schedule_next_tick(self) -> None:
        self._protocol.provider.schedule_timer(
            CONTROL_TIMER_TAG,
            self._protocol.provider.current_time() + self._battery_model.TIME_STEP,
        )

    def battery_step(self):
        """Perform a single step of the battery management model."""
        self._battery_model.manage_battery_during_flight(tuple(self.velocity))

    @property
    def battery_status(self) -> float:
        """Current battery charge as a fraction (0 to 1)."""
        return self._battery_model.get_battery_status()

    @property
    def battery_energy(self) -> float:
        """Current battery energy remaining, in Joules."""
        return self._battery_model.get_current_battery_energy()

    



