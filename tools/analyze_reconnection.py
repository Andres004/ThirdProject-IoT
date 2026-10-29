"""RNF5: automatic reconnection of the smart object, read from a serial monitor log.

A drop starts at the first WIFI_LOST or MQTT_LOST and ends at the next MQTT_CONNECTED.
For each drop the script reports:
  - outage: from the drop to MQTT_CONNECTED. It includes the time the network was off on
    purpose, so it depends on how long the hotspot was switched off.
  - mqtt_after_wifi: from WIFI_CONNECTED to MQTT_CONNECTED, the time the firmware needs to
    restore the MQTT session once WiFi is back (only when WiFi was lost).
A BOOT inside a drop means the board restarted instead of reconnecting, which fails RNF5.

PASS needs at least MIN_RECONNECTION_DROPS drops, all recovered without a restart.
"""

import argparse
from dataclasses import dataclass
from pathlib import Path

import tools_config as cfg
from report import Report
from serial_log import LogEvent, read_events


@dataclass
class Drop:
    """One connection loss: what started it, when (ms), and how it ended."""

    cause: str
    start_ms: int
    wifi_back_ms: int | None = None
    mqtt_back_ms: int | None = None
    restarted: bool = False


def find_drops(events: list[LogEvent]) -> list[Drop]:
    """Group the events into drops, from the first LOST to the next MQTT_CONNECTED or BOOT."""
    drops: list[Drop] = []
    current: Drop | None = None
    for event in events:
        if current is None:
            if event.name in (cfg.EVENT_WIFI_LOST, cfg.EVENT_MQTT_LOST):
                current = Drop(event.name, event.t_ms)
            continue
        if event.name == cfg.EVENT_WIFI_CONNECTED:
            current.wifi_back_ms = event.t_ms
        elif event.name == cfg.EVENT_MQTT_CONNECTED:
            current.mqtt_back_ms = event.t_ms
        elif event.name == cfg.EVENT_BOOT:
            current.restarted = True
        else:
            continue
        if current.mqtt_back_ms is not None or current.restarted:
            drops.append(current)
            current = None
    if current is not None:
        drops.append(current)
    return drops


def seconds(start_ms: int, end_ms: int | None) -> float | None:
    """Return the time between two uptimes in seconds, or None if the end is missing."""
    return None if end_ms is None else (end_ms - start_ms) / cfg.MS_PER_S


def text(value_s: float | None) -> str:
    """Format a time in seconds for the report, or n/a."""
    return "n/a" if value_s is None else f"{value_s:.{cfg.TIME_DECIMALS}f} s"


def analyze(report: Report, drops: list[Drop]) -> None:
    """Write one line per drop, the summary and the final verdict line."""
    outages: list[float] = []
    mqtt_after_wifi: list[float] = []
    failed = 0
    for number, drop in enumerate(drops, start=1):
        outage = seconds(drop.start_ms, drop.mqtt_back_ms)
        after_wifi = (seconds(drop.wifi_back_ms, drop.mqtt_back_ms)
                      if drop.wifi_back_ms is not None else None)
        if drop.restarted:
            status = "RESTARTED (no reconnection)"
            failed += 1
        elif outage is None:
            status = "NOT RECOVERED before the end of the log"
            failed += 1
        else:
            status = "recovered"
            outages.append(outage)
            if after_wifi is not None:
                mqtt_after_wifi.append(after_wifi)
        report.line(f"#{number} cause={drop.cause} at t_ms={drop.start_ms} outage={text(outage)} "
                    f"mqtt_after_wifi={text(after_wifi)} {status}")

    max_outage = max(outages, default=None)
    max_after_wifi = max(mqtt_after_wifi, default=None)
    report.line(f"Summary: drops={len(drops)} recovered={len(outages)} failed={failed}")
    if failed > 0:
        result = cfg.RESULT_FAIL
    elif len(drops) < cfg.MIN_RECONNECTION_DROPS:
        result = cfg.RESULT_NOT_ENOUGH_DATA
    else:
        result = cfg.RESULT_PASS
    report.line(f"RNF5 reconnection drops={len(drops)} max_outage={text(max_outage)} "
                f"max_mqtt_after_wifi={text(max_after_wifi)} -> {result}")


def main() -> None:
    """Parse the arguments, analyze the log and optionally save the report."""
    parser = argparse.ArgumentParser(
        description="RNF5: time to recover WiFi and MQTT after each drop in a serial log.")
    parser.add_argument("log", type=Path, help="serial monitor log of the smart object")
    parser.add_argument("--output", type=Path, help="also save the report to this file")
    args = parser.parse_args()

    report = Report("RNF5 reconnection analysis")
    report.line(f"Log: {args.log.name}")
    analyze(report, find_drops(read_events(args.log)))
    if args.output is not None:
        report.save(args.output)


if __name__ == "__main__":
    main()
