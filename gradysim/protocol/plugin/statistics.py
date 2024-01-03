"""
This module contains a function that creates statistics which wraps a protocol instance and it's methods. Implements
a call chain for each of the protocol interface's methods.

Use this module through the **create_statistics**][gradysim.protocol.plugin.statistics.create_statistics] method,
**never** instantiate the StatisticsProtocolWrapper directly.

Beware that this module uses monkey patching and may result in broken protocols if someone else tries to tamper with
the protocol's methods.
"""

import time
from typing import Any, Dict, List

import pandas as pd
from gradysim.protocol.plugin.dispatcher import create_dispatcher, DispatchReturn

from gradysim.protocol.interface import IProtocol


def handle_timer_srt(protocol: IProtocol, timer: str) -> DispatchReturn:
    """'
    Starts collection of statistics when a timer with a name 'statistics' is scheduled 

    Args:
        protocol: Protocol for which statistics should be collected
        timer: The name of the scheduled timer if existent
    """
    if timer == "statistics":
        _statistics_protocol_wrappers[protocol].update_srt_statistic(
            protocol.provider.current_time(), time.time()
        )

        _statistics_protocol_wrappers[protocol].update_tracked_variable_statistic(
            protocol.provider.current_time(), protocol.provider.tracked_variables
        )

        protocol.provider.schedule_timer("statistics", protocol.provider.current_time() + 0.1)
        
        return DispatchReturn.INTERRUPT

    else:
        return DispatchReturn.CONTINUE


def handle_packet_tv(protocol: IProtocol, message: str) -> DispatchReturn:
    """'
    Starts collection of tracked variables which are updated in handle packet

    Args:
        protocol: Protocol for which statistics should be collected
        message: Contains the message information  
    """
    _statistics_protocol_wrappers[protocol].update_tracked_variable_statistic(
        protocol.provider.current_time(), protocol.provider.tracked_variables
    )
    return DispatchReturn.CONTINUE


class StatisticsProtocolWrapper:
    """'
    Do not use this class directly, instead use
    [create_statistics][gradysim.protocol.plugin.statistics.create_statistics].

    Wraps the protocol's calls into a call chain. Instead of going directly to the protocol's methods calls to the
    protocol interface will be passed down a chain of registered handlers. The protocol's own method is at the end
    of the chain.
    """

    _statistics_time_list: List[Dict[str, Any]]
    _statistics_tracked_variables_list: List[Dict[str, Any]]

    def __init__(self, protocol: IProtocol, file_name_part: str):
        """
        Instantiates a protocol wrapper. Should not be instantiated directly, create a statistics using the
        [create_statistics][gradysim.protocol.plugin.statistics.create_statistics] method.

        **Do not instantiate this class directly**

        Args:
            protocol: Protocol whose calls will be wrapped
        """

        self._dispatcher = create_dispatcher(protocol)
        
        self._id = file_name_part 
        self._statistics_time_list = []
        self._statistics_tracked_variables_list = []

        protocol.provider.schedule_timer("statistics", protocol.provider.current_time() + 0.1)

    def register(self):
        """
        Registers all the methods needed for collecting the statistics
        """

        # Simulation and real time
        self._dispatcher.register_handle_timer(handle_timer_srt)

        # Tracked variables
        self._dispatcher.register_handle_packet(handle_packet_tv)

    def unregister(self):
        """
        Unregisters all the methods needed for collecting the statistics
        """

        # Simulation and real time
        self._dispatcher.unregister_handle_timer(handle_timer_srt)

        # Tracked variables
        self._dispatcher.unregister_handle_packet(handle_packet_tv)

    def update_srt_statistic(self, simulation_time: float, real_time: float) -> None:
        """
        Updates the collected statistics for simulation and real time

        Args:
            simulation_time: Current simulation time
            real_time: Current real time
        """

        self._statistics_time_list.append(
            {"simulation_time": simulation_time, "real_time": real_time}
        )

    def update_tracked_variable_statistic(
        self, simulation_time: float, tracked_variables: Dict[str, Any]
    ):
        """
        Updates the collected statistics for tracked variables and the changes based at simulation time

        Args:
            simulation_time: Current simulation time
            tracked_variables: Dictionary containing
        """

        self._statistics_tracked_variables_list.append(
            {"simulation_time": simulation_time} | tracked_variables
        )

    def create_statistic_files(self) -> None:
        """
        Creates files for the collected statistics
        """

        statistics_srt = pd.DataFrame(self._statistics_time_list)
        statistics_srt.to_csv(
            f"simulation_real_time_{self._id}_{type(self._dispatcher._protocol).__name__}_{self._dispatcher._protocol.provider.get_id()}.csv"
        )

        statistics_tv = pd.DataFrame(self._statistics_tracked_variables_list)
        statistics_tv.to_csv(
            f"tracked_variables_{self._id}_{type(self._dispatcher._protocol).__name__}_{self._dispatcher._protocol.provider.get_id()}.csv"
        )


_statistics_protocol_wrappers: Dict[IProtocol, StatisticsProtocolWrapper] = {}


def create_statistics(protocol: IProtocol, file_name_part: str = "") -> StatisticsProtocolWrapper:
    """
    Creates statistics which wraps a protocol instance and it's methods. Implements a call chain for each of the
    protocol interface's methods. The class returned from this function can be used to add functions to the call chain
    of those wrapped methods. The original method implementation is not lost.

    Is a protocol that was already wrapped is passed as an argument, return the wrapper for that protocol.

    Beware that this module uses monkey patching and may result in broken protocols if someone else tries to tamper with
    the protocol's methods.

    If you want to implement an plugin or some other behaviour that requires overriding protocol's
    methods you should use this function

    Args:
        protocol: Protocol being wrapped

    Returns:
        StatisticsProtocolWrapper instance that allows methods to be added to the call chain
    """

    global _statistics_protocol_wrappers
    if protocol not in _statistics_protocol_wrappers:
        _statistics_protocol_wrappers[protocol] = StatisticsProtocolWrapper(protocol, file_name_part)

    _statistics_protocol_wrappers[protocol].register()

    return _statistics_protocol_wrappers[protocol]


def finish_statistics(protocol: IProtocol) -> None:
    """
    Finishes the statistics. It unregisteres all registered methods and then creates the statistic files.

    Args:
        protocol: Protocol being wrapped
    """
    
    _statistics_protocol_wrappers[protocol].unregister()
    _statistics_protocol_wrappers[protocol].create_statistic_files()
