"""
This module declares a plugin that lets a protocol estimate the energy consumption and the battery status of a UAV
based on its speed and drag forces. 

Beware that this plugin needs to receive the Dynamic Velocity Mobility Telemetry, because the model is based on the UAV velocity. 
"""

import logging
from typing import Optional

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

    def __init__(self, protocol: IProtocol, configuration: BatteryPowerConfiguration,
                 rng: Optional[np.random.Generator] = None):
        """
        rng, when given, is the random generator of this node's wind. The air speed is
        then a fixed sequence indexed by the battery tick (simulated time / TIME_STEP),
        drawn from rng. The wind a node gets at time t only depends on rng, not on how
        many draws this or any other node made before, so two runs seeded alike keep the
        same wind even after their nodes take different decisions. When None the air
        speed is drawn from the global np.random at every step, as before.

        Each air speed drawn from rng is kept for configuration.random_air_speed_hold
        seconds, so the wind is piecewise constant (1 s, the default, is a new one per step).
        """
        if configuration.random_air_speed and configuration.random_air_speed_hold > 1.0 and rng is None:
            raise BatteryPowerPluginException("random_air_speed_hold > 1 s needs rng")

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
            random_air_speed=configuration.random_air_speed,
            random_air_speed_u=configuration.random_air_speed_u,
            random_air_speed_sigma=configuration.random_air_speed_sigma,
        )
        self._wind_rng = rng if configuration.random_air_speed else None
        self._wind = np.empty(0)

        self._wind_hold_ticks = max(1, int(round(configuration.random_air_speed_hold
                                                 / self._battery_model.TIME_STEP)))
        self.velocity = [0.0, 0.0]  # Initialize velocity to zero
        self._active = True

        self._tick_pending = False
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
        
            # The power model works in the body frame: (forward speed, vertical speed). The
            # handler reports the velocity in the world frame (vx, vy, vz), and a multirotor
            # flies with its body x axis along its horizontal velocity, so the forward speed
            # is the norm of (vx, vy). 
            vx, vy, vz = telemetry.current_velocity
            self.velocity = [float(np.hypot(vx, vy)), vz]
            return DispatchReturn.CONTINUE
        
        self._dispatcher.register_handle_telemetry(telemetry_handler)

    def _initialize_battery_loop(self) -> None:
            """Drives the periodic battery management model."""

            def timer_handler(_instance: IProtocol, timer: str) -> DispatchReturn:
                if timer != CONTROL_TIMER_TAG:
                    return DispatchReturn.CONTINUE
                self._tick_pending = False

                # Stopped by shutdown(): consume nothing and let the loop die by
                # not rescheduling. resume() starts it again.
                if not self._active:
                    return DispatchReturn.INTERRUPT

                self.battery_step()
                self._schedule_next_tick()

                return DispatchReturn.INTERRUPT

            self._dispatcher.register_handle_timer(timer_handler)
            self._schedule_next_tick()

    def _schedule_next_tick(self) -> None:
        self._tick_pending = True
        self._protocol.provider.schedule_timer(
            CONTROL_TIMER_TAG,
            self._protocol.provider.current_time() + self._battery_model.TIME_STEP,
        )

    def _air_speed_at_current_tick(self) -> float:
        tick = int(round(self._protocol.provider.current_time() / self._battery_model.TIME_STEP))
        period = tick // self._wind_hold_ticks
        if period >= len(self._wind):
            # Extended in blocks, so the value of a period never depends on when it was asked
            block = max(1024, period + 1 - len(self._wind))
            self._wind = np.concatenate((self._wind, self._wind_rng.normal(
                self._config.random_air_speed_u, self._config.random_air_speed_sigma, size=block)))
        return float(self._wind[period])

    def battery_step(self):
        """Perform a single step of the battery management model."""
        air_speed = self._air_speed_at_current_tick() if self._wind_rng is not None else None
        self._battery_model.manage_battery_during_flight(tuple(self.velocity), air_speed)

    @property
    def battery_status(self) -> float:
        """Current battery charge as a fraction (0 to 1)."""
        return self._battery_model.get_battery_status()

    @property
    def battery_energy(self) -> float:
        """Current battery energy remaining, in Joules."""
        return self._battery_model.get_current_battery_energy()

    def charge_battery_to_full(self) -> None:
        """Charge the battery to full capacity.

        This is a method, not a property: charging is an action with a side
        effect, so it has to be invoked explicitly.
        """
        self._battery_model.charge_battery_to_full()

    @property
    def is_active(self) -> bool:
        """Whether the battery loop is currently consuming energy."""
        return self._active

    def shutdown(self) -> None:
        """Stop the battery loop.

        The control timer reschedules itself independently of the protocol, so a
        node that is no longer flying (out of battery, landed, parked on a charging
        pad) would otherwise keep drawing flight power - at zero velocity that is
        hover power, the most expensive point of the model - until
        `manage_battery_during_flight` raises. Call this to freeze consumption.
        """
        self._active = False

    def resume(self) -> None:
        """Restart the battery loop after a `shutdown`.

        When the shutdown was less than a TIME_STEP ago, the tick scheduled before it has
        not fired yet: that tick carries the loop on. Scheduling another one would start a
        second loop and bill every step twice.
        """
        if not self._active:
            self._active = True
            if not self._tick_pending:
                self._schedule_next_tick()

    



