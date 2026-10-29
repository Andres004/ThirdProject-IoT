"""RNF4: publish rate of the distance topic on the real smart object.

The script listens to the distance topic for RATE_TEST_DURATION_S, starting at the first
reading, and stores the arrival time and the seq of every message. Readings with cm = null
are real publications (the sensor got no valid echo), so they count toward the rate and are
also reported apart. Gaps in seq show readings published by the device but not received.

Two numbers decide the result:
  - min: readings per second in the slowest complete window of RATE_WINDOW_S. Counting
    whole messages in a window has a resolution of one message (0.1/s for 10 s), and network
    jitter can move one message across a window edge, so a window passes if it is within
    that resolution of the limit. This check catches pauses and freezes.
  - mean: (readings - 1) / (time between the first and the last reading) over the whole
    test, rounded to RATE_DECIMALS. It is not affected by the window edges and must reach
    the limit, so a device that is only slightly too slow still fails.
"""

import argparse
import json
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import paho.mqtt.client as mqtt

import tools_config as cfg
from report import Report


@dataclass
class Reading:
    """One distance message: monotonic arrival time (s), seq and whether cm was null."""

    arrived_at: float
    seq: int
    is_null: bool


class PublishRateMeter:
    """Subscribe to the distance topic and record every reading that arrives.

    The readings list is only written by the paho thread and only read after close(),
    which stops that thread, so no lock is needed.
    """

    def __init__(self) -> None:
        """Create the paho client and the events used to wait for the broker and data."""
        self._connected = threading.Event()
        self._first_reading = threading.Event()
        self.readings: list[Reading] = []
        self.malformed = 0

        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=cfg.CLIENT_ID_RNF4)
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message

    def connect(self) -> bool:
        """Connect in the background and wait for the broker; return False on timeout."""
        self._client.connect_async(cfg.MQTT_HOST, cfg.MQTT_PORT, cfg.MQTT_KEEPALIVE_S)
        self._client.loop_start()
        return self._connected.wait(cfg.BROKER_CONNECT_TIMEOUT_S)

    def wait_first_reading(self) -> bool:
        """Wait until the first valid distance message arrives; return False on timeout."""
        return self._first_reading.wait(cfg.FIRST_READING_TIMEOUT_S)

    def close(self) -> None:
        """Disconnect and stop the network thread."""
        self._client.disconnect()
        self._client.loop_stop()

    def _on_connect(self, client: mqtt.Client, userdata: Any, flags: Any,
                    reason_code: Any, properties: Any) -> None:
        """Subscribe to the distance topic once the broker accepts us."""
        if reason_code.is_failure:
            return
        client.subscribe(cfg.TOPIC_DISTANCE, cfg.QOS_DISTANCE)
        self._connected.set()

    def _on_message(self, client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage) -> None:
        """Store the arrival time and seq of a reading; count payloads that cannot be parsed."""
        arrived_at = time.monotonic()
        try:
            data = json.loads(msg.payload.decode("utf-8", errors="replace"))
            reading = Reading(arrived_at, int(data["seq"]), data["cm"] is None)
        except (ValueError, KeyError, TypeError):
            self.malformed += 1
            return
        self.readings.append(reading)
        self._first_reading.set()


def run(report: Report) -> None:
    """Run the whole test and write every result line to `report`."""
    report.line(f"Broker {cfg.MQTT_HOST}:{cfg.MQTT_PORT}, topic {cfg.TOPIC_DISTANCE}, "
                f"{cfg.RATE_TEST_DURATION_S:g} s in windows of {cfg.RATE_WINDOW_S:g} s")
    meter = PublishRateMeter()
    try:
        if not meter.connect():
            report.line(f"Broker did not accept the connection in {cfg.BROKER_CONNECT_TIMEOUT_S} s")
            report.line(final_line(None, None, cfg.RESULT_NOT_ENOUGH_DATA))
            return
        if not meter.wait_first_reading():
            report.line(f"No distance reading in {cfg.FIRST_READING_TIMEOUT_S} s")
            report.line(final_line(None, None, cfg.RESULT_NOT_ENOUGH_DATA))
            return
        start = meter.readings[0].arrived_at
        try:
            time.sleep(max(0.0, start + cfg.RATE_TEST_DURATION_S - time.monotonic()))
        except KeyboardInterrupt:
            report.line("Interrupted before the end of the test")
        listened_until = time.monotonic()
    finally:
        meter.close()

    end = min(listened_until, start + cfg.RATE_TEST_DURATION_S)
    readings = [r for r in meter.readings if r.arrived_at < end]
    summarize(report, readings, start, end, meter.malformed)


def summarize(report: Report, readings: list[Reading], start: float, end: float,
              malformed: int) -> None:
    """Write one line per complete window, the summary and the final verdict line.

    Only windows that fit entirely between `start` and `end` (the listening time) count.
    """
    window_count = int((end - start) // cfg.RATE_WINDOW_S)
    rates: list[float] = []
    for index in range(window_count):
        window_start = start + index * cfg.RATE_WINDOW_S
        window_end = window_start + cfg.RATE_WINDOW_S
        count = sum(1 for r in readings if window_start <= r.arrived_at < window_end)
        rate = count / cfg.RATE_WINDOW_S
        rates.append(rate)
        report.line(f"window #{index + 1} readings={count} rate={rate:.{cfg.RATE_DECIMALS}f}/s")

    gaps, resets = count_seq_problems(readings)
    nulls = sum(1 for r in readings if r.is_null)
    report.line(f"Summary: total={len(readings)} nulls={nulls} malformed={malformed} "
                f"seq_gaps={gaps} seq_resets={resets}")

    if len(rates) < cfg.MIN_COMPLETE_WINDOWS:
        report.line(final_line(min(rates, default=None), None, cfg.RESULT_NOT_ENOUGH_DATA))
        return

    span_s = readings[-1].arrived_at - readings[0].arrived_at
    mean = round((len(readings) - 1) / span_s, cfg.RATE_DECIMALS) if span_s > 0 else 0.0
    slowest = min(rates)
    report.line(f"Window resolution: {cfg.WINDOW_RESOLUTION_PER_S:.{cfg.RATE_DECIMALS}f}/s "
                f"(one message per {cfg.RATE_WINDOW_S:g} s window)")
    passed = (slowest >= cfg.MIN_READINGS_PER_S - cfg.WINDOW_RESOLUTION_PER_S
              and mean >= cfg.MIN_READINGS_PER_S)
    report.line(final_line(slowest, mean, cfg.RESULT_PASS if passed else cfg.RESULT_FAIL))


def count_seq_problems(readings: list[Reading]) -> tuple[int, int]:
    """Return (missing seq numbers, times seq went back), comparing consecutive readings.

    A seq that goes back means the smart object restarted and its counter began again.
    """
    gaps = 0
    resets = 0
    for previous, current in zip(readings, readings[1:]):
        step = current.seq - previous.seq
        if step <= 0:
            resets += 1
        else:
            gaps += step - 1
    return gaps, resets


def final_line(slowest: float | None, mean: float | None, result: str) -> str:
    """Build the one-line verdict for RNF4."""
    decimals = cfg.RATE_DECIMALS
    min_text = "n/a" if slowest is None else f"{slowest:.{decimals}f}"
    mean_text = "n/a" if mean is None else f"{mean:.{decimals}f}"
    return (f"RNF4 publish_rate min={min_text}/s mean={mean_text}/s "
            f"limit={cfg.MIN_READINGS_PER_S}/s -> {result}")


def main() -> None:
    """Parse the arguments, run the test and optionally save the report."""
    parser = argparse.ArgumentParser(
        description="RNF4: readings per second published by the smart object on the distance "
                    "topic.")
    parser.add_argument("--output", type=Path, help="also save the report to this file")
    args = parser.parse_args()

    report = Report("RNF4 publish rate test")
    run(report)
    if args.output is not None:
        report.save(args.output)


if __name__ == "__main__":
    main()
