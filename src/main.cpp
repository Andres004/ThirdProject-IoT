/// Smart object: measures the distance with the HC-SR04, publishes it over MQTT and switches
/// three LEDs on the commands received from the mobile app or the MCP server.

#include <Arduino.h>
#include <ArduinoJson.h>
#include <math.h>
#include <string.h>

#include "EventLog.h"
#include "LedConfig.h"
#include "LedController.h"
#include "MqttConfig.h"
#include "MqttLink.h"
#include "SensorConfig.h"
#include "UltrasonicSensor.h"

UltrasonicSensor sensor(SensorConfig::PIN_TRIG, SensorConfig::PIN_ECHO);
LedController leds(LedConfig::PIN_LED_RED, LedConfig::PIN_LED_YELLOW, LedConfig::PIN_LED_WHITE);
MqttLink mqttLink;

uint32_t readingSeq = 0;
unsigned long lastSampleMs = 0;

/// Value of one LED in the leds/state payload: 1 if on, 0 if off.
unsigned int ledLevel(Led led) {
  return leds.isOn(led) ? MqttConfig::LED_LEVEL_ON : MqttConfig::LED_LEVEL_OFF;
}

/// Publishes the commanded LED state as {"red":r,"yellow":y,"white":w}, retained.
void publishLedState() {
  char payload[MqttConfig::PAYLOAD_BUFFER_BYTES];
  snprintf(payload, sizeof(payload), "{\"%s\":%u,\"%s\":%u,\"%s\":%u}",
           MqttConfig::LED_RED, ledLevel(Led::Red), MqttConfig::LED_YELLOW, ledLevel(Led::Yellow),
           MqttConfig::LED_WHITE, ledLevel(Led::White));
  EventLog::write(Event::LedState, "%s", payload);
  mqttLink.publish(MqttConfig::TOPIC_LED_STATE, payload, MqttConfig::RETAIN);
}

/// Publishes the last reading as {"seq":n,"cm":x.x}, or {"seq":n,"cm":null} if it was invalid.
void publishDistance(float distanceCm) {
  readingSeq++;
  char payload[MqttConfig::PAYLOAD_BUFFER_BYTES];
  if (isnan(distanceCm)) {
    snprintf(payload, sizeof(payload), "{\"%s\":%lu,\"%s\":null}", MqttConfig::FIELD_SEQ,
             static_cast<unsigned long>(readingSeq), MqttConfig::FIELD_CM);
  } else {
    snprintf(payload, sizeof(payload), "{\"%s\":%lu,\"%s\":%.*f}", MqttConfig::FIELD_SEQ,
             static_cast<unsigned long>(readingSeq), MqttConfig::FIELD_CM,
             MqttConfig::DISTANCE_DECIMALS, distanceCm);
  }
  mqttLink.publish(MqttConfig::TOPIC_DISTANCE, payload, MqttConfig::NO_RETAIN);
}

/// Validates a command {"led":"red|yellow|white|all","state":"on|off"}, applies it and
/// publishes the new LED state. Invalid commands are logged and ignored.
void onCommand(const char* payload, unsigned int length) {
  if (length > MqttConfig::MAX_COMMAND_LENGTH) {
    EventLog::write(Event::CmdInvalid, "reason=too_long length=%u", length);
    return;
  }
  JsonDocument doc;
  const DeserializationError error = deserializeJson(doc, payload, length);
  if (error) {
    EventLog::write(Event::CmdInvalid, "reason=bad_json error=%s payload=%.*s", error.c_str(),
                    static_cast<int>(length), payload);
    return;
  }
  const char* led = doc[MqttConfig::FIELD_LED].as<const char*>();
  const char* state = doc[MqttConfig::FIELD_STATE].as<const char*>();
  if (led == nullptr || state == nullptr) {
    EventLog::write(Event::CmdInvalid, "reason=missing_field payload=%.*s",
                    static_cast<int>(length), payload);
    return;
  }

  bool on;
  if (strcmp(state, MqttConfig::STATE_ON) == 0) {
    on = true;
  } else if (strcmp(state, MqttConfig::STATE_OFF) == 0) {
    on = false;
  } else {
    EventLog::write(Event::CmdInvalid, "reason=bad_state state=%s", state);
    return;
  }

  if (strcmp(led, MqttConfig::LED_ALL) == 0) {
    leds.setAll(on);
  } else if (strcmp(led, MqttConfig::LED_RED) == 0) {
    leds.set(Led::Red, on);
  } else if (strcmp(led, MqttConfig::LED_YELLOW) == 0) {
    leds.set(Led::Yellow, on);
  } else if (strcmp(led, MqttConfig::LED_WHITE) == 0) {
    leds.set(Led::White, on);
  } else {
    EventLog::write(Event::CmdInvalid, "reason=bad_led led=%s", led);
    return;
  }
  EventLog::write(Event::CmdRx, "led=%s state=%s", led, state);
  publishLedState();
}

/// After every (re)connection the LEDs start off and the retained state shows it.
void onConnected() {
  leds.setErrorMode(false);
  publishLedState();
}

void setup() {
  EventLog::begin();
  EventLog::write(Event::Boot, "reset_reason=%d", static_cast<int>(esp_reset_reason()));
  sensor.begin();
  leds.begin();
  mqttLink.begin(onCommand, onConnected);
}

void loop() {
  mqttLink.loop();
  leds.setErrorMode(!mqttLink.isConnected());

  const unsigned long nowMs = millis();
  if (nowMs - lastSampleMs >= SensorConfig::SAMPLE_PERIOD_MS && sensor.startMeasurement()) {
    lastSampleMs = nowMs;
  }
  if (sensor.update()) {
    publishDistance(sensor.lastDistanceCm());
  }

  leds.update();
}
