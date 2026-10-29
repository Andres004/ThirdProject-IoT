#pragma once

#include <stdint.h>

/// HC-SR04 wiring and timing. Changing the sample period here changes the publish rate.
namespace SensorConfig {

constexpr uint8_t PIN_TRIG = 27;                  // Trigger output (3.3 V is a valid high level)
constexpr uint8_t PIN_ECHO = 26;                  // Echo input through the 5 V -> 3.3 V divider

constexpr unsigned long SAMPLE_PERIOD_MS = 400;   // 2.5 readings/s: margin over the 2/s minimum
constexpr unsigned long TRIGGER_PULSE_US = 10;    // Minimum trigger pulse from the datasheet
constexpr unsigned long ECHO_TIMEOUT_US = 25000;  // The echo of 400 cm lasts ~23.3 ms

constexpr float SOUND_SPEED_CM_PER_US = 0.0343f;  // Speed of sound in air at 20 °C
constexpr float CM_PER_ECHO_US = SOUND_SPEED_CM_PER_US / 2.0f;  // The echo travels there and back
constexpr float MIN_VALID_CM = 2.0f;              // Blind zone of the sensor
constexpr float MAX_VALID_CM = 400.0f;            // Maximum range from the datasheet

}  // namespace SensorConfig
