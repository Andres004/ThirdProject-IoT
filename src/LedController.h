#pragma once

#include <Arduino.h>

/// The three LEDs of the smart object.
enum class Led { Red, Yellow, White };

/// Turns the LEDs on and off on command and blinks them all together in ERROR mode
/// (no broker connection). Leaving ERROR mode starts with every LED off.
class LedController {
 public:
  static constexpr size_t LED_COUNT = 3;

  LedController(uint8_t redPin, uint8_t yellowPin, uint8_t whitePin);

  /// Configures the pins as outputs, all LEDs off. Call once in setup().
  void begin();

  /// Turns one LED on or off. Ignored while in ERROR mode.
  void set(Led led, bool on);

  /// Turns the three LEDs on or off. Ignored while in ERROR mode.
  void setAll(bool on);

  /// Commanded state of one LED (not the blinking level of ERROR mode).
  bool isOn(Led led) const;

  /// Enters or leaves ERROR mode. Both transitions reset every LED to off.
  void setErrorMode(bool error);

  /// Drives the ERROR-mode blinking with millis(). Call on every loop().
  void update();

 private:
  /// Writes the commanded state of every LED to its pin.
  void writeCommandedState();

  /// Writes the same level to every pin.
  void writeAllPins(bool on);

  uint8_t pins_[LED_COUNT];
  bool on_[LED_COUNT] = {false, false, false};
  bool errorMode_ = false;
  bool blinkOn_ = false;
  unsigned long lastBlinkMs_ = 0;
};
