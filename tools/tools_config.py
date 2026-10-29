"""Configuration constants for the measurement scripts (RNF3 and RNF4).

The MQTT contract is imported from mcp_server/config.py instead of being copied, so the
scripts always use the same broker, topics, QoS and payload values as the MCP server,
which in turn match include/MqttConfig.h in the firmware.
"""

import sys
from pathlib import Path

# mcp_server/ is not an installed package, so its folder is added to the import path.
MCP_SERVER_DIR: Path = Path(__file__).resolve().parent.parent / "mcp_server"
sys.path.insert(0, str(MCP_SERVER_DIR))

import config as contract  # noqa: E402

# MQTT contract shared with the smart object, the app and the MCP server.
MQTT_HOST: str = contract.MQTT_HOST
MQTT_PORT: int = contract.MQTT_PORT
MQTT_KEEPALIVE_S: int = contract.MQTT_KEEPALIVE_S
TOPIC_DISTANCE: str = contract.TOPIC_DISTANCE
TOPIC_LEDS_CMD: str = contract.TOPIC_LEDS_CMD
TOPIC_LEDS_STATE: str = contract.TOPIC_LEDS_STATE
TOPIC_STATUS: str = contract.TOPIC_STATUS
QOS_DISTANCE: int = contract.QOS_DISTANCE
QOS_LEDS_CMD: int = contract.QOS_LEDS_CMD
QOS_LEDS_STATE: int = contract.QOS_LEDS_STATE
QOS_STATUS: int = contract.QOS_STATUS
STATUS_ONLINE: str = contract.STATUS_ONLINE
LED_ALL: str = contract.LED_ALL
LED_STATE_ON: str = contract.LED_STATE_ON
LED_STATE_OFF: str = contract.LED_STATE_OFF
LED_LEVEL_ON: int = contract.LED_LEVEL_ON
LED_LEVEL_OFF: int = contract.LED_LEVEL_OFF
MS_PER_S: int = contract.MS_PER_S

# Client IDs: one per script, so a script never kicks the MCP server or the app off the broker.
CLIENT_ID_RNF3: str = "sis234-g1-tool-rnf3"
CLIENT_ID_RNF4: str = "sis234-g1-tool-rnf4"

# Connection to the broker (the public HiveMQ broker has taken up to ~40 s to accept us).
BROKER_CONNECT_TIMEOUT_S: float = 60.0  # Max wait for the CONNACK before giving up

# RNF3: response time of a LED command (publish leds/cmd -> receive matching leds/state).
MAX_RESPONSE_TIME_MS: float = 1000.0  # Requirement limit for the slowest response
RESPONSE_TEST_COMMANDS: int = 20  # Commands sent in one run, alternating on/off
MIN_VALID_RESPONSES: int = 10  # Fewer answered commands than this is not enough data
RESPONSE_TIMEOUT_S: float = 3.0  # A command without a matching state after this is lost
PAUSE_BETWEEN_COMMANDS_S: float = 1.0  # Gap between commands so they never overlap
ONLINE_WAIT_TIMEOUT_S: float = 10.0  # Max wait for the retained "online" after subscribing
TEST_LED: str = "red"  # LED switched during the test
RESPONSE_PERCENTILE: int = 95  # Percentile reported in the summary (p95)
PERCENT_SCALE: int = 100  # Percentiles are expressed out of 100

# RNF4: publish rate of the distance topic.
MIN_READINGS_PER_S: float = 2.0  # Requirement limit for the slowest window
RATE_TEST_DURATION_S: float = 60.0  # Total listening time
RATE_WINDOW_S: float = 10.0  # Length of each counting window
MIN_COMPLETE_WINDOWS: int = 3  # Fewer complete windows than this is not enough data
FIRST_READING_TIMEOUT_S: float = 10.0  # Max wait for the first distance after subscribing
WINDOW_RESOLUTION_PER_S: float = 1 / RATE_WINDOW_S  # One message more or less in a window

# Report format.
RESULT_PASS: str = "PASS"
RESULT_FAIL: str = "FAIL"
RESULT_NOT_ENOUGH_DATA: str = "NOT ENOUGH DATA"
TIME_DECIMALS: int = 1  # Decimals for times in ms
RATE_DECIMALS: int = 2  # Decimals for readings per second
TIMESTAMP_FORMAT: str = "%Y-%m-%d %H:%M:%S"  # Date and time written at the top of a report
