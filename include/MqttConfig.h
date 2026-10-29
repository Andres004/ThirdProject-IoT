#pragma once

#include <stddef.h>
#include <stdint.h>

/// MQTT contract shared by the smart object, the mobile app and the MCP server.
/// The same topics and payloads are mirrored in mcp_server/config.py.
namespace MqttConfig {

// Public HiveMQ broker: no user/password, so it is not a secret.
// The hostname is used (never a fixed IP) because the broker IP can change.
constexpr char BROKER_HOST[] = "broker.hivemq.com";
constexpr uint16_t BROKER_PORT = 1883;            // Plain TCP (no TLS) on the public broker
constexpr uint16_t KEEPALIVE_S = 15;              // Broker declares us dead after 1.5 x this
constexpr uint16_t SOCKET_TIMEOUT_S = 2;          // Max wait for a network read inside PubSubClient
constexpr uint32_t CONNECT_TIMEOUT_S = 2;         // Max wait for the TCP connect to the broker
constexpr uint16_t BUFFER_SIZE_BYTES = 256;       // Largest MQTT packet we send or accept
constexpr char CLIENT_ID_PREFIX[] = "sis234-g1-oi-";  // + MAC address = unique client id
constexpr size_t CLIENT_ID_BUFFER_BYTES = 32;     // Prefix + 12 hex digits + terminator

// Every topic starts with the group prefix so we do not collide with other groups.
constexpr char TOPIC_DISTANCE[] = "sis234/grupo1/distance";    // OI -> app, MCP
constexpr char TOPIC_LED_COMMAND[] = "sis234/grupo1/leds/cmd"; // app, MCP -> OI
constexpr char TOPIC_LED_STATE[] = "sis234/grupo1/leds/state"; // OI -> app, MCP (retained)
constexpr char TOPIC_STATUS[] = "sis234/grupo1/status";        // OI -> app, MCP (retained, LWT)

constexpr uint8_t COMMAND_SUBSCRIBE_QOS = 1;      // Commands must not be lost
constexpr uint8_t STATUS_WILL_QOS = 1;
constexpr bool RETAIN = true;
constexpr bool NO_RETAIN = false;

constexpr char STATUS_ONLINE[] = "online";
constexpr char STATUS_OFFLINE[] = "offline";

// JSON field names and values of the payloads.
constexpr char FIELD_SEQ[] = "seq";               // distance: reading counter, starts at 1
constexpr char FIELD_CM[] = "cm";                 // distance: centimeters or null
constexpr char FIELD_LED[] = "led";               // leds/cmd: which LED
constexpr char FIELD_STATE[] = "state";           // leds/cmd: on or off
constexpr char LED_RED[] = "red";                 // Also the keys of the leds/state payload
constexpr char LED_YELLOW[] = "yellow";
constexpr char LED_WHITE[] = "white";
constexpr char LED_ALL[] = "all";                 // Targets the three LEDs at once
constexpr char STATE_ON[] = "on";
constexpr char STATE_OFF[] = "off";
constexpr uint8_t LED_LEVEL_ON = 1;               // Value of a lit LED in leds/state
constexpr uint8_t LED_LEVEL_OFF = 0;              // Value of a dark LED in leds/state
constexpr uint8_t DISTANCE_DECIMALS = 1;          // Decimals published for cm

constexpr unsigned int MAX_COMMAND_LENGTH = 64;   // Longer commands are rejected
constexpr unsigned long MQTT_RETRY_INTERVAL_MS = 2000;
constexpr unsigned long WIFI_RETRY_INTERVAL_MS = 10000;

}  // namespace MqttConfig
