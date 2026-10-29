#pragma once

#include <Arduino.h>

/// Events written to the serial log. The log is the evidence for stability and reconnection.
enum class Event {
  Boot,
  WifiConnecting,
  WifiConnected,
  WifiLost,
  WifiRetry,
  MqttConnecting,
  MqttConnected,
  MqttLost,
  MqttRetry,
  Pub,
  PubFailed,
  CmdRx,
  CmdInvalid,
  LedState
};

/// Serial log with a fixed format, easy to parse by the analysis scripts:
/// [t_ms=   123456] EVENT_NAME       details
class EventLog {
 public:
  static constexpr unsigned long SERIAL_BAUD = 115200;  // Same as monitor_speed in platformio.ini
  static constexpr size_t DETAILS_BUFFER_BYTES = 160;  // Longest details text per line

  /// Opens the serial port. Call once at the start of setup().
  static void begin();

  /// Writes one line with the uptime in ms, the event name and printf-style details.
  static void write(Event event, const char* format, ...)
      __attribute__((format(printf, 2, 3)));

 private:
  /// Name of the event as it appears in the log.
  static const char* name(Event event);
};
