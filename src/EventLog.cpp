#include "EventLog.h"

#include <stdarg.h>

void EventLog::write(Event event, const char* format, ...) {
  char details[DETAILS_BUFFER_BYTES];
  va_list args;
  va_start(args, format);
  vsnprintf(details, sizeof(details), format, args);
  va_end(args);
  Serial.printf("[t_ms=%9lu] %-16s %s\n", millis(), name(event), details);
}

const char* EventLog::name(Event event) {
  switch (event) {
    case Event::Boot:           return "BOOT";
    case Event::WifiConnecting: return "WIFI_CONNECTING";
    case Event::WifiConnected:  return "WIFI_CONNECTED";
    case Event::WifiLost:       return "WIFI_LOST";
    case Event::WifiRetry:      return "WIFI_RETRY";
    case Event::MqttConnecting: return "MQTT_CONNECTING";
    case Event::MqttConnected:  return "MQTT_CONNECTED";
    case Event::MqttLost:       return "MQTT_LOST";
    case Event::MqttRetry:      return "MQTT_RETRY";
    case Event::Pub:            return "PUB";
    case Event::PubFailed:      return "PUB_FAILED";
    case Event::CmdRx:          return "CMD_RX";
    case Event::CmdInvalid:     return "CMD_INVALID";
    case Event::LedState:       return "LED_STATE";
  }
  return "UNKNOWN";
}
