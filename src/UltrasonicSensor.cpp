#include "UltrasonicSensor.h"

#include "SensorConfig.h"

UltrasonicSensor::UltrasonicSensor(uint8_t trigPin, uint8_t echoPin)
    : trigPin_(trigPin), echoPin_(echoPin) {}

void UltrasonicSensor::begin() {
  pinMode(trigPin_, OUTPUT);
  digitalWrite(trigPin_, LOW);
  pinMode(echoPin_, INPUT);
  attachInterruptArg(digitalPinToInterrupt(echoPin_), onEchoChange, this, CHANGE);
}

bool UltrasonicSensor::startMeasurement() {
  if (state_ != State::Idle) {
    return false;
  }
  armed_ = false;
  echoStarted_ = false;
  echoDone_ = false;
  digitalWrite(trigPin_, HIGH);
  triggerStartUs_ = micros();
  state_ = State::Trigger;
  return true;
}

bool UltrasonicSensor::update() {
  const uint32_t nowUs = micros();

  switch (state_) {
    case State::Idle:
      return false;

    case State::Trigger:
      if (nowUs - triggerStartUs_ < SensorConfig::TRIGGER_PULSE_US) {
        return false;
      }
      digitalWrite(trigPin_, LOW);
      waitStartUs_ = nowUs;
      armed_ = true;
      state_ = State::WaitEcho;
      return false;

    case State::WaitEcho:
      if (echoDone_) {
        lastDistanceCm_ = echoToCm(echoEndUs_ - echoStartUs_);
      } else if (nowUs - waitStartUs_ >= SensorConfig::ECHO_TIMEOUT_US) {
        armed_ = false;
        lastDistanceCm_ = NAN;
      } else {
        return false;
      }
      state_ = State::Idle;
      return true;
  }
  return false;
}

float UltrasonicSensor::lastDistanceCm() const {
  return lastDistanceCm_;
}

void IRAM_ATTR UltrasonicSensor::onEchoChange(void* arg) {
  UltrasonicSensor* sensor = static_cast<UltrasonicSensor*>(arg);
  if (!sensor->armed_) {
    return;
  }
  const uint32_t nowUs = micros();
  if (digitalRead(sensor->echoPin_) == HIGH) {
    sensor->echoStartUs_ = nowUs;
    sensor->echoStarted_ = true;
  } else if (sensor->echoStarted_) {
    sensor->echoEndUs_ = nowUs;
    sensor->echoDone_ = true;
    sensor->armed_ = false;
  }
}

float UltrasonicSensor::echoToCm(uint32_t echoUs) {
  const float distanceCm = static_cast<float>(echoUs) * SensorConfig::CM_PER_ECHO_US;
  if (distanceCm < SensorConfig::MIN_VALID_CM || distanceCm > SensorConfig::MAX_VALID_CM) {
    return NAN;
  }
  return distanceCm;
}
