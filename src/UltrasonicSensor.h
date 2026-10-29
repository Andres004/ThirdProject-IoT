#pragma once

#include <Arduino.h>

/// Non-blocking HC-SR04 driver.
/// A measurement goes through Idle -> Trigger -> WaitEcho. The trigger pulse is timed with
/// micros() and the echo edges are captured by an interrupt, so loop() never waits for the
/// sensor. An invalid reading (no echo or out of range) is reported as NAN.
class UltrasonicSensor {
 public:
  UltrasonicSensor(uint8_t trigPin, uint8_t echoPin);

  /// Configures the pins and attaches the echo interrupt. Call once in setup().
  void begin();

  /// Starts a new measurement. Returns false if the previous one has not finished yet.
  bool startMeasurement();

  /// Advances the state machine. Call on every loop(). Returns true exactly once per
  /// measurement, when the result is ready in lastDistanceCm().
  bool update();

  /// Distance of the last finished measurement in centimeters, or NAN if it was invalid.
  float lastDistanceCm() const;

 private:
  enum class State { Idle, Trigger, WaitEcho };

  /// Echo interrupt: stores the time of the rising and falling edges of the current echo.
  static void IRAM_ATTR onEchoChange(void* arg);

  /// Converts the echo duration to centimeters, or NAN if it is outside the valid range.
  static float echoToCm(uint32_t echoUs);

  uint8_t trigPin_;
  uint8_t echoPin_;
  State state_ = State::Idle;
  uint32_t triggerStartUs_ = 0;
  uint32_t waitStartUs_ = 0;
  float lastDistanceCm_ = NAN;

  // Shared with the interrupt. The ISR only writes while armed_ is true, and it disarms
  // itself after the falling edge, so loop() can read the times safely once echoDone_ is set.
  volatile bool armed_ = false;
  volatile bool echoStarted_ = false;
  volatile bool echoDone_ = false;
  volatile uint32_t echoStartUs_ = 0;
  volatile uint32_t echoEndUs_ = 0;
};
