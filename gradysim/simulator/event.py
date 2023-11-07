"""
As an event-based simulator one of the main components in the simulation is an event loop, that's the focus of this
module. Events are compact classes containing a timestamp and a callback. Events are inserted into the event loop which
is organized as a heap to keep the events with the smallest timestamps on top. At every simulation iteration the
simulator class grabs the event with the smallest timestamp and executes its callback.

Events are created by handlers. Protocols indirectly interact with them through the provider interface they have access
to. These events, when executed, cause effects on the network nodes, mainly observed through calls to the protocol
interface methods like handle_timer.
"""

import heapq
from dataclasses import dataclass
from typing import Callable, List, Optional


@dataclass
class Event:
    """
    Dataclass representing a single event. Will be placed inside the simulation loop. Shouldn't be instantiated
    directly, but through the `EventLoop.schedule_event` method.
    """

    timestamp: float
    """Simulation time in seconds when the event will fire"""
    callback: Callable
    """Any callable with no parameters. Will be executed when the event fires"""
    context: str
    """
    Context in which the event will be executed. 
    This is used in logging to identify where the callback is being executed.
    """

    def __lt__(self, other):
        return self.timestamp < other.timestamp


class EventLoopException(Exception):
    pass


class EventLoop:
    """
    Event loop central to the event-based simulation. Is implemented as a min-heap populated by `Event` instances ordered
    by their timestamps. Generally only the [`Simulator`][gradysim.simulator.simulation.Simulator] will call the `pop_event`
    method, a handler should only need to use the `schedule_event` method.
    """
    _event_heap: List[Event]
    _current_time: float

    def __init__(self):
        """
        Creates an event loop
        """
        self._event_heap = []
        self._current_time = 0

    def schedule_event(self, timestamp: float, callback: Callable, context: str = "") -> None:
        """
        Creates an event instance with the information provided as args and inserts it into the event heap.

        Args:
            timestamp: Simulation time in seconds when the event should fire
            callback: Any callable with no arguments
            context: Context where the callable executes. Useful for logging.
        """
        if timestamp < self.current_time:
            raise EventLoopException(f"Could not schedule event: tried to schedule at {timestamp} which is "
                                     f"earlier than the current time {self.current_time}. ")

        heapq.heappush(self._event_heap, Event(timestamp, callback, context))

    def pop_event(self) -> Event:
        """
        Removes an event from the top of the event heap and returns it. If called when the event heap is empty it will
        raise EventLoopException.

        Returns: The event popped.

        """
        if len(self._event_heap) == 0:
            raise EventLoopException("Could not pop event: the event queue is empty")

        event = heapq.heappop(self._event_heap)
        self._current_time = event.timestamp
        return event

    def peek_event(self) -> Optional[Event]:
        """
        Peeks at the event at the top of the event heap without removing it. Returns None if the event heap is empty.

        Returns:
            The event at the top of the event heap or None if it's empty
        """
        if len(self._event_heap) == 0:
            return None
        return self._event_heap[0]

    def clear(self) -> None:
        """
        Clears the event heap
        """
        self._event_heap.clear()

    @property
    def current_time(self) -> float:
        """
        Returns the timestamp of the last event to be removed from the heap.
        This represents the current simulation time.

        Returns:
            The current simulation fime
        """
        return self._current_time

    def __len__(self) -> int:
        """
        By calling len() on the EventLoop you can check how many events are queued in the event heap.

        Returns:
            Number of events in the event heap
        """
        return len(self._event_heap)
