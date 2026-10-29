#pragma once

#include <Arduino.h>
#include <PubSubClient.h>
#include <WiFi.h>

#include "MqttConfig.h"

/// WiFi + MQTT connection of the smart object, never blocking loop() for long.
/// WiFi and MQTT are retried on their own intervals with millis(). On every MQTT connect it
/// registers the last will (status = offline), subscribes to the command topic, publishes
/// status = online and calls the connected handler so main can publish the LED state.
class MqttLink {
 public:
  /// Receives the raw payload of every message on the command topic.
  using CommandHandler = void (*)(const char* payload, unsigned int length);
  /// Called right after each successful MQTT connection.
  using ConnectedHandler = void (*)();

  MqttLink();

  /// Starts WiFi without waiting and configures the MQTT client. Call once in setup().
  void begin(CommandHandler onCommand, ConnectedHandler onConnected);

  /// Keeps WiFi and MQTT alive and processes incoming messages. Call on every loop().
  void loop();

  /// True while both WiFi and the MQTT session are up.
  bool isConnected();

  /// Publishes with QoS 0 (the only QoS PubSubClient can publish) and logs PUB or PUB_FAILED.
  bool publish(const char* topic, const char* payload, bool retained);

 private:
  /// Detects WiFi changes and retries every WIFI_RETRY_INTERVAL_MS. Returns true if WiFi is up.
  bool ensureWifi();

  /// Detects a lost session and retries every MQTT_RETRY_INTERVAL_MS while WiFi is up.
  void ensureMqtt();

  /// One connection attempt with last will, subscription and online status.
  void connectMqtt();

  /// Forwards messages of the command topic to the command handler.
  void handleMessage(char* topic, uint8_t* payload, unsigned int length);

  WiFiClient wifiClient_;
  PubSubClient mqttClient_;
  char clientId_[MqttConfig::CLIENT_ID_BUFFER_BYTES] = "";
  CommandHandler onCommand_ = nullptr;
  ConnectedHandler onConnected_ = nullptr;
  bool wifiUp_ = false;
  bool mqttUp_ = false;
  bool mqttAttemptNow_ = false;
  unsigned long lastWifiAttemptMs_ = 0;
  unsigned long lastMqttAttemptMs_ = 0;
};
