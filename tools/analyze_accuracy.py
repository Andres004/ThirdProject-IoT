"""RNF2: accuracy of the distance against a ruler, measured live on the distance topic.

For each reference distance in REFERENCE_DISTANCES_CM the operator places a flat object at
that distance from the sensor, measured with a ruler, and presses Enter. The script then
takes SAMPLES_PER_DISTANCE valid readings (null readings are counted apart) and reports the
mean, the error of the mean, the largest single error and the standard deviation.

The working range is the longest run of consecutive reference distances where every single
reading is within MAX_ERROR_CM. Distances outside it are reported, not hidden. PASS needs a
working range of at least MIN_RANGE_POINTS distances.
"""

import argparse
import json
import queue
import statistics
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import paho.mqtt.client as mqtt

import tools_config as cfg
from report import Report


@dataclass
class DistanceResult:
    """Readings taken at one reference distance and the errors against it."""

    reference_cm: float
    readings_cm: list[float]
    nulls: int

    def complete(self) -> bool:
        """Return True if all the requested valid readings were collected."""
        return len(self.readings_cm) >= cfg.SAMPLES_PER_DISTANCE

    def max_error_cm(self) -> float:
        """Return the largest absolute error of a single reading."""
        return max(abs(r - self.reference_cm) for r in self.readings_cm)

    def within_limit(self) -> bool:
        """Return True if the distance was fully measured and every reading is within limit."""
        return self.complete() and self.max_error_cm() <= cfg.MAX_ERROR_CM


class AccuracyMeter:
    """Subscribe to the distance topic and hand the readings to the main thread on request."""

    def __init__(self) -> None:
        """Create the paho client, the connection event and the readings queue."""
        self._connected = threading.Event()
        self._readings: queue.Queue[float | None] = queue.Queue()
        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=cfg.CLIENT_ID_RNF2)
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message

    def connect(self) -> bool:
        """Connect in the background and wait for the broker; return False on timeout."""
        self._client.connect_async(cfg.MQTT_HOST, cfg.MQTT_PORT, cfg.MQTT_KEEPALIVE_S)
        self._client.loop_start()
        return self._connected.wait(cfg.BROKER_CONNECT_TIMEOUT_S)

    def measure(self, reference_cm: float) -> DistanceResult:
        """Drop old readings, then collect SAMPLES_PER_DISTANCE valid ones or until timeout."""
        while not self._readings.empty():
            self._readings.get_nowait()
        result = DistanceResult(reference_cm, [], 0)
        deadline = time.monotonic() + cfg.SAMPLE_TIMEOUT_S
        while not result.complete():
            remaining_s = deadline - time.monotonic()
            if remaining_s <= 0:
                break
            try:
                value = self._readings.get(timeout=remaining_s)
            except queue.Empty:
                break
            if value is None:
                result.nulls += 1
            else:
                result.readings_cm.append(value)
        return result

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
        """Queue the cm value of a reading (None for a null reading); ignore bad payloads."""
        try:
            cm = json.loads(msg.payload.decode("utf-8", errors="replace"))["cm"]
            self._readings.put(None if cm is None else float(cm))
        except (ValueError, KeyError, TypeError):
            return


def report_distance(report: Report, result: DistanceResult) -> None:
    """Write the statistics of one reference distance."""
    d = cfg.CM_DECIMALS
    if not result.readings_cm:
        report.line(f"ref={result.reference_cm:g} cm: no valid reading (nulls={result.nulls})")
        return
    mean = statistics.mean(result.readings_cm)
    stdev = statistics.stdev(result.readings_cm) if len(result.readings_cm) > 1 else 0.0
    status = "OK" if result.within_limit() else "OUT"
    if not result.complete():
        status = f"INCOMPLETE ({len(result.readings_cm)}/{cfg.SAMPLES_PER_DISTANCE})"
    report.line(f"ref={result.reference_cm:g} cm n={len(result.readings_cm)} "
                f"nulls={result.nulls} mean={mean:.{d}f} cm "
                f"mean_error={mean - result.reference_cm:+.{d}f} cm "
                f"max_error={result.max_error_cm():.{d}f} cm stdev={stdev:.{d}f} cm {status}")


def working_range(results: list[DistanceResult]) -> list[DistanceResult]:
    """Return the longest run of consecutive measured distances that are within the limit."""
    best: list[DistanceResult] = []
    current: list[DistanceResult] = []
    for result in results:
        current = current + [result] if result.within_limit() else []
        if len(current) > len(best):
            best = current
    return best


def summarize(report: Report, results: list[DistanceResult]) -> None:
    """Write the working range, the distances outside it and the final verdict line."""
    measured = [r for r in results if r.complete()]
    in_range = working_range(results)
    d = cfg.CM_DECIMALS
    outside = [r for r in measured if r not in in_range]
    for result in outside:
        report.line(f"Outside the working range: {result.reference_cm:g} cm "
                    f"(max error {result.max_error_cm():.{d}f} cm)")

    if len(measured) < cfg.MIN_RANGE_POINTS:
        report.line(f"RNF2 accuracy max_error=n/a range=n/a limit={cfg.MAX_ERROR_CM} cm "
                    f"-> {cfg.RESULT_NOT_ENOUGH_DATA}")
        return
    if len(in_range) < cfg.MIN_RANGE_POINTS:
        report.line(f"RNF2 accuracy max_error=n/a range=none limit={cfg.MAX_ERROR_CM} cm "
                    f"-> {cfg.RESULT_FAIL}")
        return
    max_error = max(r.max_error_cm() for r in in_range)
    report.line(f"RNF2 accuracy max_error={max_error:.{d}f} cm "
                f"range={in_range[0].reference_cm:g}-{in_range[-1].reference_cm:g} cm "
                f"limit={cfg.MAX_ERROR_CM} cm -> {cfg.RESULT_PASS}")


def run(report: Report) -> None:
    """Guide the operator through every reference distance and write the results."""
    report.line(f"Broker {cfg.MQTT_HOST}:{cfg.MQTT_PORT}, {cfg.SAMPLES_PER_DISTANCE} valid "
                f"readings per distance, limit {cfg.MAX_ERROR_CM} cm")
    meter = AccuracyMeter()
    try:
        if not meter.connect():
            report.line(f"Broker did not accept the connection in {cfg.BROKER_CONNECT_TIMEOUT_S} s")
            report.line(f"RNF2 accuracy max_error=n/a range=n/a limit={cfg.MAX_ERROR_CM} cm "
                        f"-> {cfg.RESULT_NOT_ENOUGH_DATA}")
            return
        results: list[DistanceResult] = []
        for reference_cm in cfg.REFERENCE_DISTANCES_CM:
            answer = input(f"Place the object at {reference_cm:g} cm and press Enter "
                           f"('{cfg.SKIP_ANSWER}' + Enter to skip): ")
            if answer.strip().lower() == cfg.SKIP_ANSWER:
                report.line(f"ref={reference_cm:g} cm: skipped")
                results.append(DistanceResult(reference_cm, [], 0))
                continue
            result = meter.measure(reference_cm)
            report_distance(report, result)
            results.append(result)
        summarize(report, results)
    finally:
        meter.close()


def main() -> None:
    """Parse the arguments, run the guided test and optionally save the report."""
    parser = argparse.ArgumentParser(
        description="RNF2: error of the measured distance against a ruler at fixed distances.")
    parser.add_argument("--output", type=Path, help="also save the report to this file")
    args = parser.parse_args()

    report = Report("RNF2 accuracy test")
    run(report)
    if args.output is not None:
        report.save(args.output)


if __name__ == "__main__":
    main()
