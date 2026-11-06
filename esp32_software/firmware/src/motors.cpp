#include "motors.h"
#include <cmath>
#include <cstring>

namespace {
constexpr int pwmPins[] = {25, 26}, in1[] = {21, 22}, in2[] = {17, 23};
constexpr int encA[] = {35, 27}, encB[] = {34, 16};
volatile int32_t pulses[2] = {};
portMUX_TYPE mux = portMUX_INITIALIZER_UNLOCKED;
void IRAM_ATTR encoderLeft() {
    portENTER_CRITICAL_ISR(&mux);
    pulses[0] += digitalRead(encA[0]) ? 1 : -1;
    portEXIT_CRITICAL_ISR(&mux);
}
void IRAM_ATTR encoderRight() {
    portENTER_CRITICAL_ISR(&mux);
    pulses[1] += digitalRead(encA[1]) ? 1 : -1;
    portEXIT_CRITICAL_ISR(&mux);
}
}
void Motors::begin() {
    for (unsigned i = 0; i < 2; ++i) {
        pinMode(in1[i], OUTPUT); pinMode(in2[i], OUTPUT);
        digitalWrite(in1[i], LOW); digitalWrite(in2[i], LOW);
        ledcSetup(i, 20000, 8); ledcAttachPin(pwmPins[i], i); ledcWrite(i, 0);
        // GPIO34/35 have no internal pull-up; board/external bias is required.
        pinMode(encA[i], INPUT); pinMode(encB[i], INPUT);
    }
    attachInterrupt(encB[0], encoderLeft, RISING);
    attachInterrupt(encB[1], encoderRight, RISING);
}
void Motors::write(unsigned i, float pwm) {
    if (!config::motorsEnabled) pwm = 0;
    this->pwm[i] = constrain(pwm, -255.f, 255.f);
    int duty = lroundf(constrain(pwm * config::motorSign[i], -255.f, 255.f));
    ledcWrite(i, 0);
    digitalWrite(in1[i], duty < 0); digitalWrite(in2[i], duty > 0);
    ledcWrite(i, abs(duty));
}
void Motors::stop() {
    drive_.reset();
    for (unsigned i = 0; i < 2; ++i) { controller_[i].reset(); guard_[i].reset(); target[i] = 0; write(i, 0); }
}
void Motors::update(float v, float omega, float dt) {
    int32_t count[2];
    portENTER_CRITICAL(&mux);
    for (unsigned i = 0; i < 2; ++i) { count[i] = pulses[i]; pulses[i] = 0; }
    portEXIT_CRITICAL(&mux);
    for (unsigned i = 0; i < 2; ++i) encoder[i] += count[i];
    if (!config::calibrated() || !std::isfinite(dt) || dt <= 0 || dt > .1f) {
        if (config::calibrated()) fault = "control_overrun";
        stop(); return;
    }
    drive_.update(v, omega, config::trackWidth, config::maxWheelSpeed, config::acceleration, dt);
    for (unsigned i = 0; i < 2; ++i) target[i] = drive_.wheel[i];
    for (unsigned i = 0; i < 2; ++i) {
        speed[i] = count[i]*config::encoderSign[i]*PI*config::wheelDiameter/config::pulsesPerTurn[i]/dt;
        float output = 0;
        if (target[i] == 0) { controller_[i].reset(); guard_[i].reset(); }
        else {
            output = controller_[i].update(target[i], speed[i], dt);
            float distancePerPulse = PI*config::wheelDiameter/config::pulsesPerTurn[i];
            if (const char* code = guard_[i].check(controller_[i].target, speed[i], dt, distancePerPulse)) {
                if (!strcmp(code, "encoder_no_response"))
                    fault = i == 0 ? "encoder_no_response_left" : "encoder_no_response_right";
                else fault = code;
            }
        }
        write(i, fault ? 0 : output);
    }
    measuredV = (speed[0]+speed[1])/2;
    measuredOmega = (speed[1]-speed[0])/config::trackWidth;
    if (fault) stop();
}
