#pragma once

#include <stdint.h>

/// LED wiring (220 ohm in series, cathode to GND) and error-mode blinking.
namespace LedConfig {

constexpr uint8_t PIN_LED_RED = 25;
constexpr uint8_t PIN_LED_YELLOW = 33;
constexpr uint8_t PIN_LED_WHITE = 32;

constexpr unsigned long ERROR_BLINK_INTERVAL_MS = 250;  // Toggle every 250 ms = 2 Hz blink

}  // namespace LedConfig
