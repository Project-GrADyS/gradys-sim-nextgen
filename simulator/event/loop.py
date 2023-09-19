import heapq
from typing import Tuple, Callable, List

Event = Tuple[float, Callable]


class EventLoop:
    _event_queue: List[Event]
    current_time: float

    def __init__(self):
        self._event_queue = []
        self.current_time = 0

    def schedule_event(self, timestamp: float, callback: Callable):
        heapq.heappush(self._event_queue, (timestamp, callback))

    def pop_event(self) -> Event:
        event = heapq.heappop(self._event_queue)
        self.current_time = event[0]
        return event

    def size(self):
        return len(self._event_queue)

    def clear(self):
        self._event_queue.clear()

