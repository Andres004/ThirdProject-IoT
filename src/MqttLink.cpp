#include "MqttLink.h"

#include <string.h>

#include "EventLog.h"
#include "Secrets.h"

MqttLink::MqttLink() : mqttClient_(wifiClient_) {}

void MqttLink::begin(CommandHandler onCommand, ConnectedHandler onConnected) {
  onCommand_ = onCommand;
  onConnected_ = onConnected;

  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);
  WiFi.setAutoReconnect(false);

  uint8_t mac[6];
  WiFi.macAddress(mac);
  snprintf(clientId_, sizeof(clientId_), "%s%02X%02X%02X%02X%02X%02X",
           MqttConfig::CLIENT_ID_PREFIX, mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);

  wifiClient_.setTimeout(MqttConfig::CONNECT_TIMEOUT_S);
  mqttClient_.setServer(MqttConfig::BROKER_HOST, MqttConfig::BROKER_PORT);
  mqttClient_.setKeepAlive(MqttConfig::KEEPALIVE_S);
  mqttClient_.setSocketTimeout(MqttConfig::SOCKET_TIMEOUT_S);
  mqttClient_.setBufferSize(MqttConfig::BUFFER_SIZE_BYTES);
  mqttClient_.setCallback([this](char* topic, uint8_t* payload, unsigned int length) {
    handleMessage(topic, payload, length);
  });

  EventLog::write(Event::WifiConnecting, "ssid=%s client_id=%s", Secrets::WIFI_SSID, clientId_);
  WiFi.begin(Secrets::WIFI_SSID, Secrets::WIFI_PASSWORD);
  lastWifiAttemptMs_ = millis();
}

void MqttLink::loop() {
  mqttClient_.loop();
  if (ensureWifi()) {
    ensureMqtt();
  } else if (mqttUp_) {
    mqttUp_ = false;
    EventLog::write(Event::MqttLost, "reason=wifi_lost");
  }
}

bool MqttLink::isConnected() {
  return wifiUp_ && mqttClient_.connected();
}

bool MqttLink::publish(const char* topic, const char* payload, bool retained) {
  if (!isConnected()) {
    EventLog::write(Event::PubFailed, "topic=%s payload=%s reason=not_connected", topic, payload);
    return false;
  }
  if (!mqttClient_.publish(topic, payload, retained)) {
    EventLog::write(Event::PubFailed, "topic=%s payload=%s reason=write_failed", topic, payload);
    return false;
  }
  EventLog::write(Event::Pub, "topic=%s payload=%s", topic, payload);
  return true;
}

bool MqttLink::ensureWifi() {
  const unsigned long nowMs = millis();

  if (WiFi.status() == WL_CONNECTED) {
    if (!wifiUp_) {
      wifiUp_ = true;
      mqttAttemptNow_ = true;
      EventLog::write(Event::WifiConnected, "ip=%s rssi_dbm=%d",
                      WiFi.localIP().toString().c_str(), WiFi.RSSI());
    }
    return true;
  }

  if (wifiUp_) {
    wifiUp_ = false;
    lastWifiAttemptMs_ = nowMs;
    // Close the socket without sending DISCONNECT, so the broker publishes the last will.
    wifiClient_.stop();
    EventLog::write(Event::WifiLost, "status=%d", static_cast<int>(WiFi.status()));
  }
  if (nowMs - lastWifiAttemptMs_ >= MqttConfig::WIFI_RETRY_INTERVAL_MS) {
    lastWifiAttemptMs_ = nowMs;
    EventLog::write(Event::WifiRetry, "status=%d", static_cast<int>(WiFi.status()));
    WiFi.disconnect();
    WiFi.begin(Secrets::WIFI_SSID, Secrets::WIFI_PASSWORD);
  }
  return false;
}

void MqttLink::ensureMqtt() {
  if (mqttClient_.connected()) {
    return;
  }
  if (mqttUp_) {
    mqttUp_ = false;
    EventLog::write(Event::MqttLost, "state=%d", mqttClient_.state());
  }
  const unsigned long nowMs = millis();
  if (mqttAttemptNow_ || nowMs - lastMqttAttemptMs_ >= MqttConfig::MQTT_RETRY_INTERVAL_MS) {
    mqttAttemptNow_ = false;
    connectMqtt();
    lastMqttAttemptMs_ = millis();
  }
}

void MqttLink::connectMqtt() {
  EventLog::write(Event::MqttConnecting, "host=%s port=%u",
                  MqttConfig::BROKER_HOST, MqttConfig::BROKER_PORT);
  const unsigned long startMs = millis();
  const bool connected = mqttClient_.connect(clientId_, MqttConfig::TOPIC_STATUS,
                                             MqttConfig::STATUS_WILL_QOS, MqttConfig::RETAIN,
                                             MqttConfig::STATUS_OFFLINE);
  const unsigned long tookMs = millis() - startMs;
  if (!connected) {
    EventLog::write(Event::MqttRetry, "state=%d took_ms=%lu", mqttClient_.state(), tookMs);
    return;
  }
  mqttUp_ = true;
  EventLog::write(Event::MqttConnected, "took_ms=%lu", tookMs);
  mqttClient_.subscribe(MqttConfig::TOPIC_LED_COMMAND, MqttConfig::COMMAND_SUBSCRIBE_QOS);
  publish(MqttConfig::TOPIC_STATUS, MqttConfig::STATUS_ONLINE, MqttConfig::RETAIN);
  if (onConnected_ != nullptr) {
    onConnected_();
  }
}

void MqttLink::handleMessage(char* topic, uint8_t* payload, unsigned int length) {
  if (strcmp(topic, MqttConfig::TOPIC_LED_COMMAND) != 0 || onCommand_ == nullptr) {
    return;
  }
  onCommand_(reinterpret_cast<const char*>(payload), length);
}
