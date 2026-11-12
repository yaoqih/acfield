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
    const unsigned channel = config::wheelChannels[i];
    ledcWrite(channel, 0);
    digitalWrite(in1[channel], duty < 0); digitalWrite(in2[channel], duty > 0);
    ledcWrite(channel, abs(duty));
}
void Motors::stop() {
    drive_.reset();
    for (unsigned i = 0; i < 2; ++i) { controller_[i].reset(); guard_[i].reset(); target[i] = 0; write(i, 0); }
}
void Motors::update(float v, float omega, float dt) {
    int32_t count[2];
    portENTER_CRITICAL(&mux);
    for (unsigned i = 0; i < 2; ++i) count[i] = pulses[config::wheelChannels[i]];
    pulses[0] = pulses[1] = 0;
    portEXIT_CRITICAL(&mux);
    for (unsigned i = 0; i < 2; ++i) encoder[i] += count[i];
    if (!config::calibrated() || !std::isfinite(dt) || dt <= 0 || dt > .1f) {
        if (config::calibrated()) fault = "control_overrun";
        for (auto& window : speedWindow_) window.reset();
        stop(); return;
    }
    drive_.update(v, omega, config::trackWidth, config::maxWheelSpeed);
    for (unsigned i = 0; i < 2; ++i) target[i] = drive_.wheel[i];
    // Saturate the open-loop pair together, retaining the requested wheel-speed
    // ratio when either duty reaches 255. Never feed encoder noise into duty.
    const float peak = fmaxf(fabsf(target[0]), fabsf(target[1]));
    const float openLoopGain = peak > 0 ? fminf(config::feedForward, 255.f/peak) : config::feedForward;
    for (unsigned i = 0; i < 2; ++i) {
        const float distancePerPulse = PI*config::wheelDiameter/config::pulsesPerTurn[i];
        const float rawSpeed = count[i]*config::encoderSign[i]*distancePerPulse/dt;
        speed[i] = config::encoderDiagnostic ? rawSpeed :
            speedWindow_[i].update(count[i], dt, config::encoderSign[i]*distancePerPulse);
        float output = 0;
        if (target[i] == 0) { controller_[i].reset(); guard_[i].reset(); }
        else if (config::encoderDiagnostic || !config::motorClosedLoop) {
            controller_[i].reset(); guard_[i].reset();
            output = config::encoderDiagnostic ? diagnosticPwm(target[i]) : openLoopGain*target[i];
        }
        else {
            output = controller_[i].update(target[i], speed[i], dt);
            if (const char* code = guard_[i].check(controller_[i].target, speed[i], dt, distancePerPulse, count[i] != 0)) {
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
