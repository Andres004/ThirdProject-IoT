"""Parser for the serial monitor logs of the smart object (src/EventLog.cpp)."""

import json
import re
from dataclasses import dataclass
from pathlib import Path

import tools_config as cfg

_LINE = re.compile(cfg.LOG_LINE_PATTERN)
_DISTANCE_PREFIX = f"topic={cfg.TOPIC_DISTANCE} payload="


@dataclass
class LogEvent:
    """One line of the event log: uptime in ms, event name and free-text details."""

    t_ms: int
    name: str
    details: str

    def distance_seq(self) -> int | None:
        """Return the seq of a distance PUB, or None for any other event."""
        if self.name != cfg.EVENT_PUB or not self.details.startswith(_DISTANCE_PREFIX):
            return None
        try:
            return int(json.loads(self.details[len(_DISTANCE_PREFIX):])["seq"])
        except (ValueError, KeyError, TypeError):
            return None


def read_events(path: Path) -> list[LogEvent]:
    """Return the events of a log in order, skipping boot-loader noise and other lines."""
    events: list[LogEvent] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = _LINE.search(line)
        if match is not None:
            events.append(LogEvent(int(match.group(1)), match.group(2), match.group(3).strip()))
    return events


def split_by_boot(events: list[LogEvent]) -> list[list[LogEvent]]:
    """Split the events into runs that each start at a BOOT, because t_ms restarts at 0."""
    runs: list[list[LogEvent]] = []
    for event in events:
        if event.name == cfg.EVENT_BOOT or not runs:
            runs.append([])
        runs[-1].append(event)
    return runs
