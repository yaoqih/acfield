#pragma once
#include <Arduino.h>
#include "wheel_control.h"
#include "encoder_guard.h"
#include "differential_drive.h"

class Motors {
public:
    void begin();
    void update(float v, float omega, float dt);
    void stop();
    float measuredV = 0, measuredOmega = 0, speed[2] = {}, target[2] = {}, pwm[2] = {};
    int64_t encoder[2] = {};
    const char* fault = nullptr;
private:
    DifferentialDrive drive_;
    WheelControl controller_[2];
    EncoderGuard guard_[2];
    void write(unsigned side, float pwm);
};
