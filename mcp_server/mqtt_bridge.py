"""MQTT bridge between the MCP tools and the smart object."""

import json
import logging
import threading
import time
from dataclasses import dataclass
from typing import Any

import paho.mqtt.client as mqtt

import config

logger = logging.getLogger("mqtt-bridge")


@dataclass
class Stamped:
    """A value together with the monotonic time (seconds) when it arrived."""

    value: Any
    received_at: float

    def age_s(self) -> float:
        """Return how many seconds ago the value arrived."""
        return time.monotonic() - self.received_at


class MqttBridge:
    """Keep an MQTT connection open and cache the latest data from the smart object.

    The paho network loop runs in a background thread, so every cached value is
    protected by one lock. A condition on that lock lets set_led() wait until the
    smart object confirms a command on the LED state topic.
    """

    def __init__(self) -> None:
        """Create the paho client and register the callbacks."""
        self._lock = threading.Lock()
        self._state_changed = threading.Condition(self._lock)
        self._broker_connected = False
        self._distance: Stamped | None = None
        self._led_state: Stamped | None = None
        self._status: Stamped | None = None

        self._client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2, client_id=config.MQTT_CLIENT_ID
        )
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message
        self._client.reconnect_delay_set(
            min_delay=config.MQTT_RECONNECT_MIN_DELAY_S,
            max_delay=config.MQTT_RECONNECT_MAX_DELAY_S,
        )

    def start(self) -> None:
        """Start connecting in the background; paho keeps retrying if the broker is down."""
        logger.info("Connecting to %s:%d as %s",
                    config.MQTT_HOST, config.MQTT_PORT, config.MQTT_CLIENT_ID)
        self._client.connect_async(config.MQTT_HOST, config.MQTT_PORT, config.MQTT_KEEPALIVE_S)
        self._client.loop_start()

    def stop(self) -> None:
        """Stop the network thread and close the connection."""
        self._client.loop_stop()
        self._client.disconnect()
        logger.info("MQTT client stopped")

    def is_broker_connected(self) -> bool:
        """Return True while the MQTT session with the broker is open."""
        with self._lock:
            return self._broker_connected

    def get_distance(self) -> Stamped | None:
        """Return the last distance reading {'seq', 'cm'} or None if none arrived."""
        with self._lock:
            return self._distance

    def get_led_state(self) -> Stamped | None:
        """Return the last LED state {'red', 'yellow', 'white'} or None if none arrived."""
        with self._lock:
            return self._led_state

    def get_status(self) -> Stamped | None:
        """Return the last smart object status ('online'/'offline') or None if unknown."""
        with self._lock:
            return self._status

    def send_led_command(self, led: str, state: str) -> bool:
        """Publish one LED command with QoS 1; return False if paho rejected it."""
        payload = json.dumps({"led": led, "state": state}, separators=(",", ":"))
        info = self._client.publish(config.TOPIC_LEDS_CMD, payload, qos=config.QOS_LEDS_CMD)
        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            logger.error("Publish failed on %s: %s", config.TOPIC_LEDS_CMD,
                         mqtt.error_string(info.rc))
            return False
        logger.info("Published %s to %s", payload, config.TOPIC_LEDS_CMD)
        return True

    def wait_for_led_state(self, expected: dict[str, int], since: float,
                           timeout_s: float) -> Stamped | None:
        """Wait until a LED state newer than `since` matches `expected`.

        Only the LEDs listed in `expected` are compared. Returns the matching
        state, or None when the timeout expires.
        """
        def matches() -> bool:
            state = self._led_state
            if state is None or state.received_at < since:
                return False
            return all(state.value.get(led) == value for led, value in expected.items())

        with self._state_changed:
            if self._state_changed.wait_for(matches, timeout=timeout_s):
                return self._led_state
            return None

    def _on_connect(self, client: mqtt.Client, userdata: Any, flags: Any,
                    reason_code: Any, properties: Any) -> None:
        """Subscribe on every connect, so a reconnect restores the subscriptions."""
        if reason_code.is_failure:
            logger.error("Broker refused the connection: %s", reason_code)
            return
        with self._lock:
            self._broker_connected = True
        logger.info("Connected to broker")
        client.subscribe([
            (config.TOPIC_DISTANCE, config.QOS_DISTANCE),
            (config.TOPIC_LEDS_STATE, config.QOS_LEDS_STATE),
            (config.TOPIC_STATUS, config.QOS_STATUS),
        ])

    def _on_disconnect(self, client: mqtt.Client, userdata: Any, flags: Any,
                       reason_code: Any, properties: Any) -> None:
        """Mark the broker as unreachable; paho reconnects on its own."""
        with self._lock:
            self._broker_connected = False
        logger.warning("Disconnected from broker: %s (will retry)", reason_code)

    def _on_message(self, client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage) -> None:
        """Parse a message and store it with its arrival time."""
        text = msg.payload.decode("utf-8", errors="replace").strip()
        now = time.monotonic()
        if msg.topic == config.TOPIC_STATUS:
            self._store_status(text, now)
        elif msg.topic == config.TOPIC_DISTANCE:
            self._store_distance(text, now)
        elif msg.topic == config.TOPIC_LEDS_STATE:
            self._store_led_state(text, now)

    def _store_status(self, text: str, now: float) -> None:
        """Store 'online'/'offline'; anything else is ignored."""
        if text not in (config.STATUS_ONLINE, config.STATUS_OFFLINE):
            logger.warning("Ignored invalid status: %r", text)
            return
        with self._lock:
            self._status = Stamped(text, now)
        logger.info("Smart object status: %s", text)

    def _store_distance(self, text: str, now: float) -> None:
        """Store a {'seq', 'cm'} reading; cm may be None for an invalid measurement."""
        try:
            data = json.loads(text)
            reading = {"seq": int(data["seq"]),
                       "cm": None if data["cm"] is None else float(data["cm"])}
        except (ValueError, KeyError, TypeError):
            logger.warning("Ignored invalid distance payload: %r", text)
            return
        with self._lock:
            self._distance = Stamped(reading, now)
        logger.debug("Distance seq=%d cm=%s", reading["seq"], reading["cm"])

    def _store_led_state(self, text: str, now: float) -> None:
        """Store a {'red', 'yellow', 'white'} state and wake up any waiting command."""
        try:
            data = json.loads(text)
            state = {led: int(data[led]) for led in config.LED_NAMES}
        except (ValueError, KeyError, TypeError):
            logger.warning("Ignored invalid LED state payload: %r", text)
            return
        with self._state_changed:
            self._led_state = Stamped(state, now)
            self._state_changed.notify_all()
        logger.info("LED state: %s", state)
