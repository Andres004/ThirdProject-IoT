"""RNF3: response time of a LED command on the real smart object.

For each command the script takes time.perf_counter(), publishes {"led": ..., "state": ...}
on leds/cmd with QoS 1, and stops the clock when a new leds/state arrives in which that LED
has the requested value. The measured path is the full round trip
PC -> broker -> smart object -> broker -> PC, so it includes the confirmation on the way
back. It is therefore an upper bound of the one-way path app -> broker -> smart object
that RNF3 asks for.

A command without a matching state within RESPONSE_TIMEOUT_S counts as lost. The result is
PASS only if no command was lost and the slowest response is within MAX_RESPONSE_TIME_MS.
"""

import argparse
import json
import statistics
import threading
import time
from pathlib import Path
from typing import Any

import paho.mqtt.client as mqtt

import tools_config as cfg
from report import Report


class ResponseTimeMeter:
    """Send LED commands one at a time and time how long the smart object takes to confirm."""

    def __init__(self) -> None:
        """Create the paho client and the events used to wait for the broker and the device."""
        self._connected = threading.Event()
        self._online = threading.Event()
        self._confirmed = threading.Event()
        self._expected_level: int | None = None
        self._confirmed_at = 0.0

        self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=cfg.CLIENT_ID_RNF3)
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message

    def connect(self) -> bool:
        """Connect in the background and wait for the broker; return False on timeout."""
        self._client.connect_async(cfg.MQTT_HOST, cfg.MQTT_PORT, cfg.MQTT_KEEPALIVE_S)
        self._client.loop_start()
        return self._connected.wait(cfg.BROKER_CONNECT_TIMEOUT_S)

    def wait_online(self) -> bool:
        """Wait for the retained "online" status of the smart object; return False on timeout."""
        return self._online.wait(cfg.ONLINE_WAIT_TIMEOUT_S)

    def measure(self, state: str) -> float | None:
        """Switch TEST_LED to `state` and return the confirmation time in ms, or None if lost."""
        self._confirmed.clear()
        self._expected_level = cfg.LED_LEVEL_ON if state == cfg.LED_STATE_ON else cfg.LED_LEVEL_OFF
        sent_at = time.perf_counter()
        self._publish_command(cfg.TEST_LED, state)
        confirmed = self._confirmed.wait(cfg.RESPONSE_TIMEOUT_S)
        self._expected_level = None
        if not confirmed:
            return None
        return (self._confirmed_at - sent_at) * cfg.MS_PER_S

    def close(self) -> None:
        """Turn every LED off, then disconnect."""
        if self._connected.is_set():
            self._publish_command(cfg.LED_ALL, cfg.LED_STATE_OFF).wait_for_publish(
                cfg.RESPONSE_TIMEOUT_S)
        self._client.disconnect()
        self._client.loop_stop()

    def _publish_command(self, led: str, state: str) -> mqtt.MQTTMessageInfo:
        """Publish one command on leds/cmd with the contract QoS."""
        payload = json.dumps({"led": led, "state": state}, separators=(",", ":"))
        return self._client.publish(cfg.TOPIC_LEDS_CMD, payload, qos=cfg.QOS_LEDS_CMD)

    def _on_connect(self, client: mqtt.Client, userdata: Any, flags: Any,
                    reason_code: Any, properties: Any) -> None:
        """Subscribe to the status and LED state topics once the broker accepts us."""
        if reason_code.is_failure:
            return
        client.subscribe([(cfg.TOPIC_STATUS, cfg.QOS_STATUS),
                          (cfg.TOPIC_LEDS_STATE, cfg.QOS_LEDS_STATE)])
        self._connected.set()

    def _on_message(self, client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage) -> None:
        """Track the online status and stop the clock on the first matching LED state."""
        arrived_at = time.perf_counter()
        text = msg.payload.decode("utf-8", errors="replace").strip()
        if msg.topic == cfg.TOPIC_STATUS:
            if text == cfg.STATUS_ONLINE:
                self._online.set()
            else:
                self._online.clear()
            return
        if self._expected_level is None or self._confirmed.is_set():
            return
        try:
            level = int(json.loads(text)[cfg.TEST_LED])
        except (ValueError, KeyError, TypeError):
            return
        if level == self._expected_level:
            self._confirmed_at = arrived_at
            self._confirmed.set()


def run(report: Report) -> None:
    """Run the whole test and write every result line to `report`."""
    report.line(f"Broker {cfg.MQTT_HOST}:{cfg.MQTT_PORT}, LED {cfg.TEST_LED}, "
                f"{cfg.RESPONSE_TEST_COMMANDS} commands, timeout {cfg.RESPONSE_TIMEOUT_S} s")
    meter = ResponseTimeMeter()
    try:
        if not meter.connect():
            report.line(f"Broker did not accept the connection in {cfg.BROKER_CONNECT_TIMEOUT_S} s")
            report.line(final_line(None, cfg.RESULT_NOT_ENOUGH_DATA))
            return
        if not meter.wait_online():
            report.line(f"Smart object not online after {cfg.ONLINE_WAIT_TIMEOUT_S} s")
            report.line(final_line(None, cfg.RESULT_NOT_ENOUGH_DATA))
            return

        times_ms: list[float] = []
        lost = 0
        state = cfg.LED_STATE_OFF
        for number in range(1, cfg.RESPONSE_TEST_COMMANDS + 1):
            state = cfg.LED_STATE_ON if state == cfg.LED_STATE_OFF else cfg.LED_STATE_OFF
            elapsed_ms = meter.measure(state)
            if elapsed_ms is None:
                lost += 1
                report.line(f"#{number} state={state} LOST (no confirmation in "
                            f"{cfg.RESPONSE_TIMEOUT_S} s)")
            else:
                times_ms.append(elapsed_ms)
                report.line(f"#{number} state={state} time_ms={elapsed_ms:.{cfg.TIME_DECIMALS}f}")
            time.sleep(cfg.PAUSE_BETWEEN_COMMANDS_S)

        summarize(report, times_ms, lost)
    finally:
        meter.close()


def summarize(report: Report, times_ms: list[float], lost: int) -> None:
    """Write the summary statistics and the final PASS/FAIL/NOT ENOUGH DATA line."""
    if len(times_ms) < cfg.MIN_VALID_RESPONSES:
        report.line(f"Summary: n={len(times_ms)} lost={lost} "
                    f"(fewer than {cfg.MIN_VALID_RESPONSES} responses)")
        report.line(final_line(max(times_ms, default=None), cfg.RESULT_NOT_ENOUGH_DATA))
        return

    decimals = cfg.TIME_DECIMALS
    percentile = statistics.quantiles(times_ms, n=cfg.PERCENT_SCALE, method="inclusive")
    p95 = percentile[cfg.RESPONSE_PERCENTILE - 1]
    slowest = max(times_ms)
    report.line(f"Summary: n={len(times_ms)} lost={lost} "
                f"min={min(times_ms):.{decimals}f} ms "
                f"mean={statistics.mean(times_ms):.{decimals}f} ms "
                f"p{cfg.RESPONSE_PERCENTILE}={p95:.{decimals}f} ms "
                f"max={slowest:.{decimals}f} ms")
    passed = lost == 0 and slowest <= cfg.MAX_RESPONSE_TIME_MS
    report.line(final_line(slowest, cfg.RESULT_PASS if passed else cfg.RESULT_FAIL))


def final_line(slowest_ms: float | None, result: str) -> str:
    """Build the one-line verdict for RNF3."""
    value = "n/a" if slowest_ms is None else f"{slowest_ms:.{cfg.TIME_DECIMALS}f}"
    return (f"RNF3 response_time max={value} ms limit={cfg.MAX_RESPONSE_TIME_MS:g} ms "
            f"-> {result}")


def main() -> None:
    """Parse the arguments, run the test and optionally save the report."""
    parser = argparse.ArgumentParser(
        description="RNF3: time from a LED command on leds/cmd to its confirmation on leds/state.")
    parser.add_argument("--output", type=Path, help="also save the report to this file")
    args = parser.parse_args()

    report = Report("RNF3 response time test")
    run(report)
    if args.output is not None:
        report.save(args.output)


if __name__ == "__main__":
    main()
