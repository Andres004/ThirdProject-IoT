"""Configuration constants for the MCP server.

The MQTT contract (topics, QoS, payload keys) must match include/MqttConfig.h in the firmware.
The broker host and port can be overridden with environment variables (see .env.example).
"""

import os

# Broker: public HiveMQ, plain TCP, no credentials. Always a hostname, never an IP.
MQTT_HOST: str = os.environ.get("MQTT_HOST", "broker.hivemq.com")
MQTT_PORT: int = int(os.environ.get("MQTT_PORT", "1883"))  # TCP port without TLS
MQTT_KEEPALIVE_S: int = 15  # Seconds between pings; same value as the smart object
MQTT_CLIENT_ID_PREFIX: str = "sis234-g1-mcp"  # The process ID is appended to keep it unique
MQTT_RECONNECT_MIN_DELAY_S: int = 1  # First wait before retrying a lost connection
MQTT_RECONNECT_MAX_DELAY_S: int = 30  # Upper bound for the exponential retry wait

# Topics shared with the smart object and the mobile app.
TOPIC_DISTANCE: str = "sis234/grupo1/distance"
TOPIC_LEDS_CMD: str = "sis234/grupo1/leds/cmd"
TOPIC_LEDS_STATE: str = "sis234/grupo1/leds/state"
TOPIC_STATUS: str = "sis234/grupo1/status"

# QoS per topic, as declared in the protocol table.
QOS_DISTANCE: int = 0  # Lost readings are acceptable; the next one arrives in 0.4 s
QOS_LEDS_CMD: int = 1  # A command must reach the broker at least once
QOS_LEDS_STATE: int = 0  # PubSubClient on the ESP32 can only publish with QoS 0
QOS_STATUS: int = 1  # The LWT is published by the broker with QoS 1

# Payload values.
STATUS_ONLINE: str = "online"
STATUS_OFFLINE: str = "offline"
LED_NAMES: tuple[str, ...] = ("red", "yellow", "white")  # Individual LEDs on the smart object
LED_ALL: str = "all"  # Pseudo LED name that targets the three LEDs at once
LED_STATE_ON: str = "on"
LED_STATE_OFF: str = "off"
LED_STATES: tuple[str, ...] = (LED_STATE_ON, LED_STATE_OFF)
LED_LEVEL_ON: int = 1  # Value of a lit LED in the leds/state payload
LED_LEVEL_OFF: int = 0  # Value of a dark LED in the leds/state payload
CMD_MAX_LENGTH_BYTES: int = 64  # The smart object rejects longer command payloads

# Timing rules for the MCP tools.
CONFIRM_TIMEOUT_S: float = 3.0  # Max wait for leds/state after publishing a command
MAX_READING_AGE_S: float = 5.0  # A distance older than this is reported as stale (12 periods)
AGE_DECIMALS: int = 1  # Decimals shown for ages in seconds
MS_PER_S: int = 1000  # Converts seconds to milliseconds

# Logging (always to stderr; stdout carries the MCP protocol).
LOG_FORMAT: str = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
