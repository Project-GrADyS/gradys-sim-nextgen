import heapq
from typing import Callable, List, Optional


class Event:
    def __init__(self, timestamp: float, callback: Callable, handler: str):
        self.timestamp = timestamp
        self.callback = callback
        self.handler = handler

    def __lt__(self, other):
        return self.timestamp < other.timestamp


class EventLoopException(Exception):
    pass


class EventLoop:
    _event_queue: List[Event]
    _current_time: float

    def __init__(self):
        self._event_queue = []
        self._current_time = 0

    def schedule_event(self, timestamp: float, callback: Callable, handler: str = ""):
        if timestamp < self.current_time:
            raise EventLoopException(f"Could not schedule event: tried to schedule at {timestamp} which is "
                                     f"earlier than the current time {self.current_time}. ")

        heapq.heappush(self._event_queue, Event(timestamp, callback, handler))

    def pop_event(self) -> Event:
        if len(self._event_queue) == 0:
            raise EventLoopException("Could not pop event: the event queue is empty")

        event = heapq.heappop(self._event_queue)
        self._current_time = event.timestamp
        return event

    def peek_event(self) -> Optional[Event]:
        if len(self._event_queue) == 0:
            return None
        return self._event_queue[0]

    def clear(self):
        self._event_queue.clear()

    @property
    def current_time(self):
        return self._current_time

    def __len__(self):
        return len(self._event_queue)
