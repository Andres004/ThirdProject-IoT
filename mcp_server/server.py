"""MCP server for the SIS-234 group 1 smart object.

Exposes tools that let Claude read the HC-SR04 distance and switch the three LEDs
(red, yellow, white) of the ESP32. Every exchange goes through the MQTT broker.
"""

import logging
import sys
import time
from typing import Any

from mcp.server.mcpserver import MCPServer

import config
from mqtt_bridge import MqttBridge

# Logs go to stderr: with the stdio transport, stdout carries the MCP protocol.
logging.basicConfig(level=logging.INFO, format=config.LOG_FORMAT, stream=sys.stderr)
logger = logging.getLogger("mcp-server")

bridge = MqttBridge()
mcp = MCPServer("sis234-g1-smart-object")


def _oi_online() -> bool | None:
    """Return True/False from the LWT status, or None if it was never received."""
    status = bridge.get_status()
    if status is None:
        return None
    return status.value == config.STATUS_ONLINE


@mcp.tool()
def get_distance() -> dict[str, Any]:
    """Get the latest distance measured by the smart object's ultrasonic sensor (HC-SR04).

    Use this whenever the user asks how far the object is, or anything about the distance.
    Returns a dict with:
      - cm: distance in centimeters (1 decimal), or null if the last reading was invalid
        (no echo or out of range).
      - seq: sequence number of the reading (increases by 1 per reading).
      - age_s: seconds since the reading arrived.
      - online: whether the smart object is connected (null if unknown).
      - error: present only when the value should not be trusted; explain it to the user.
    """
    reading = bridge.get_distance()
    online = _oi_online()
    if reading is None:
        return {"online": online, "error": "No distance reading has been received yet."}
    result: dict[str, Any] = {
        "cm": reading.value["cm"],
        "seq": reading.value["seq"],
        "age_s": round(reading.age_s(), config.AGE_DECIMALS),
        "online": online,
    }
    if online is False:
        result["error"] = "The smart object is offline; this is the last known reading."
    elif reading.age_s() > config.MAX_READING_AGE_S:
        result["error"] = (f"The reading is stale (older than {config.MAX_READING_AGE_S} s); "
                           "the smart object may have stopped publishing.")
    elif reading.value["cm"] is None:
        result["error"] = "The sensor got no valid echo (nothing in range or out of range)."
    return result


@mcp.tool()
def set_led(led: str, state: str) -> dict[str, Any]:
    """Turn one LED of the smart object on or off and wait for the device to confirm it.

    The led argument is "red", "yellow", "white", or "all" for the three LEDs at once.
    The state argument is "on" or "off".
    For combined requests, call this tool several times. Example: "turn on the red LED
    and turn off the others" -> set_led("all", "off") and then set_led("red", "on").
    Returns a dict with ok (true/false), the confirmed LED state reported by the device
    as {"red": 0|1, "yellow": 0|1, "white": 0|1}, or an error message.
    """
    led = led.strip().lower()
    state = state.strip().lower()
    valid_leds = (*config.LED_NAMES, config.LED_ALL)
    if led not in valid_leds:
        return {"ok": False, "error": f"Invalid led '{led}'. Use one of {list(valid_leds)}."}
    if state not in config.LED_STATES:
        return {"ok": False,
                "error": f"Invalid state '{state}'. Use one of {list(config.LED_STATES)}."}
    if not bridge.is_broker_connected():
        return {"ok": False, "error": "The MCP server is not connected to the MQTT broker."}
    if _oi_online() is False:
        return {"ok": False, "error": "The smart object is offline; the command was not sent."}

    target_leds = config.LED_NAMES if led == config.LED_ALL else (led,)
    level = config.LED_LEVEL_ON if state == config.LED_STATE_ON else config.LED_LEVEL_OFF
    expected = {name: level for name in target_leds}
    sent_at = time.monotonic()
    if not bridge.send_led_command(led, state):
        return {"ok": False, "error": "The command could not be published to the broker."}

    confirmed = bridge.wait_for_led_state(expected, sent_at, config.CONFIRM_TIMEOUT_S)
    if confirmed is None:
        return {"ok": False,
                "error": (f"No confirmation from the smart object within "
                          f"{config.CONFIRM_TIMEOUT_S} s; the LED may not have changed.")}
    return {"ok": True, "leds": confirmed.value,
            "confirm_ms": round((confirmed.received_at - sent_at) * config.MS_PER_S)}


@mcp.tool()
def get_status() -> dict[str, Any]:
    """Get the overall health of the system: broker link, smart object status and LEDs.

    Use this when the user asks whether the device is connected or which LEDs are on.
    Returns a dict with:
      - broker_connected: whether this MCP server is connected to the MQTT broker.
      - smart_object: "online", "offline" or "unknown" (from its last-will status).
      - leds: last reported state {"red": 0|1, "yellow": 0|1, "white": 0|1}, or null.
      - leds_age_s: seconds since that LED state arrived, or null.
    """
    status = bridge.get_status()
    leds = bridge.get_led_state()
    return {
        "broker_connected": bridge.is_broker_connected(),
        "smart_object": status.value if status else "unknown",
        "leds": leds.value if leds else None,
        "leds_age_s": round(leds.age_s(), config.AGE_DECIMALS) if leds else None,
    }


def main() -> None:
    """Start the MQTT bridge and serve the MCP tools over stdio until the client closes."""
    bridge.start()
    try:
        logger.info("Starting MCP server")
        mcp.run()
    except KeyboardInterrupt:
        logger.info("Interrupted, shutting down")
    finally:
        bridge.stop()


if __name__ == "__main__":
    main()
