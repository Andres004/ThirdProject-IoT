#include "LedController.h"

#include "LedConfig.h"

LedController::LedController(uint8_t redPin, uint8_t yellowPin, uint8_t whitePin)
    : pins_{redPin, yellowPin, whitePin} {}

void LedController::begin() {
  for (size_t i = 0; i < LED_COUNT; i++) {
    pinMode(pins_[i], OUTPUT);
  }
  writeCommandedState();
}

void LedController::set(Led led, bool on) {
  if (errorMode_) {
    return;
  }
  const size_t index = static_cast<size_t>(led);
  on_[index] = on;
  digitalWrite(pins_[index], on ? HIGH : LOW);
}

void LedController::setAll(bool on) {
  if (errorMode_) {
    return;
  }
  for (size_t i = 0; i < LED_COUNT; i++) {
    on_[i] = on;
  }
  writeCommandedState();
}

bool LedController::isOn(Led led) const {
  return on_[static_cast<size_t>(led)];
}

void LedController::setErrorMode(bool error) {
  if (error == errorMode_) {
    return;
  }
  errorMode_ = error;
  for (size_t i = 0; i < LED_COUNT; i++) {
    on_[i] = false;
  }
  blinkOn_ = false;
  lastBlinkMs_ = millis();
  writeCommandedState();
}

void LedController::update() {
  if (!errorMode_) {
    return;
  }
  const unsigned long nowMs = millis();
  if (nowMs - lastBlinkMs_ >= LedConfig::ERROR_BLINK_INTERVAL_MS) {
    lastBlinkMs_ = nowMs;
    blinkOn_ = !blinkOn_;
    writeAllPins(blinkOn_);
  }
}

void LedController::writeCommandedState() {
  for (size_t i = 0; i < LED_COUNT; i++) {
    digitalWrite(pins_[i], on_[i] ? HIGH : LOW);
  }
}

void LedController::writeAllPins(bool on) {
  for (size_t i = 0; i < LED_COUNT; i++) {
    digitalWrite(pins_[i], on ? HIGH : LOW);
  }
}
