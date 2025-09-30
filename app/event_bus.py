"""Simple publish/subscribe event bus."""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable, DefaultDict, Dict, List

EventCallback = Callable[[Dict[str, Any]], None]


class EventBus:
    """Very small synchronous event bus."""

    def __init__(self) -> None:
        self._subscribers: DefaultDict[str, List[EventCallback]] = defaultdict(list)

    def subscribe(self, event: str, callback: EventCallback) -> None:
        if callback not in self._subscribers[event]:
            self._subscribers[event].append(callback)

    def publish(self, event: str, payload: Dict[str, Any]) -> None:
        for callback in list(self._subscribers[event]):
            callback(payload)


event_bus = EventBus()
