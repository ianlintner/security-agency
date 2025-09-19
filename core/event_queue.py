from collections import deque
from typing import Optional

from core.models import OrchestrationEvent


class EventQueue:
    """
    In-memory event queue abstraction.
    Can be extended later to use Redis, Kafka, etc.
    """

    def __init__(self):
        self._queue = deque()

    def publish(self, event: OrchestrationEvent) -> None:
        """Publish an orchestration event to the queue."""
        self._queue.append(event)

    def consume(self) -> Optional[OrchestrationEvent]:
        """Consume the next orchestration event from the queue."""
        if self._queue:
            return self._queue.popleft()
        return None

    def size(self) -> int:
        """Return the number of events currently in the queue."""
        return len(self._queue)
