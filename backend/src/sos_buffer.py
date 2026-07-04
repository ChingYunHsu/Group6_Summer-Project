"""In-memory buffer for incoming SOS webhook events.

The SOS endpoint is high-priority/low-latency, so it appends the raw event
straight into this process-local buffer instead of taking a DB round trip
on the request path. The SSE stream (api/realtime.py) drains it to push
each event to connected map clients.
"""

from collections import deque

_buffer = deque()


def push_sos_event(event: dict) -> None:
    _buffer.append(event)


def drain_sos_events() -> list:
    """Pop and return every buffered event since the last drain."""
    drained = []
    while _buffer:
        drained.append(_buffer.popleft())
    return drained
