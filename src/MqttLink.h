#pragma once

#include <Arduino.h>
#include <PubSubClient.h>
#include <WiFi.h>
#include <lwip/ip_addr.h>

#include <atomic>

#include "MqttConfig.h"

/// WiFi + MQTT connection of the smart object, never blocking loop() for long.
/// WiFi and MQTT are retried on their own intervals with millis(). Each MQTT attempt first
/// resolves the broker hostname with the asynchronous lwIP DNS (loop() keeps running while it
/// waits) and then connects to the resolved address. On every MQTT connect it registers the
/// last will (status = offline), subscribes to the command topic, publishes status = online and
/// calls the connected handler so main can publish the LED state.
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

  /// Detects a lost session and starts a new attempt every MQTT_RETRY_INTERVAL_MS while WiFi
  /// is up, or follows the DNS lookup of the attempt in progress.
  void ensureMqtt();

  /// Starts an attempt by asking lwIP for the broker address without waiting for the answer.
  void startDnsLookup();

  /// Connects when the DNS answer has arrived, or gives up after DNS_TIMEOUT_MS.
  void checkDnsLookup();

  /// One connection attempt to the resolved broker address, with last will, subscription and
  /// online status. Bounded by CONNECT_TIMEOUT_S (TCP) and SOCKET_TIMEOUT_S (CONNACK).
  void connectMqtt(const IPAddress& brokerIp, unsigned long dnsMs);

  /// Forwards messages of the command topic to the command handler.
  void handleMessage(char* topic, uint8_t* payload, unsigned int length);

  /// lwIP DNS callback. Runs in the network task, so it only stores the result in atomics.
  static void onDnsFound(const char* name, const ip_addr_t* address, void* arg);

  WiFiClient wifiClient_;
  PubSubClient mqttClient_;
  char clientId_[MqttConfig::CLIENT_ID_BUFFER_BYTES] = "";
  CommandHandler onCommand_ = nullptr;
  ConnectedHandler onConnected_ = nullptr;
  bool wifiUp_ = false;
  bool mqttUp_ = false;
  bool mqttAttemptNow_ = false;
  bool dnsPending_ = false;
  unsigned long lastWifiAttemptMs_ = 0;
  unsigned long lastMqttAttemptMs_ = 0;
  unsigned long dnsStartMs_ = 0;

  // Written by onDnsFound() in the network task and read by loop(): the address is stored
  // before the done flag, so loop() always reads the address of a finished lookup.
  std::atomic<uint32_t> dnsResultIp_{0};
  std::atomic<bool> dnsDone_{false};
};
