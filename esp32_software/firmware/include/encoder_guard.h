#pragma once
#include <cmath>
#include "config.h"

class EncoderGuard {
public:
    const char* check(float target, float measured, float dt, float distancePerPulse) {
        if (target != 0 && measured == 0) {
            quietMs_ += lroundf(dt*1000);
            missingDistance_ += fabsf(target)*dt;
        } else { quietMs_ = 0; missingDistance_ = 0; }
        reverseMs_ = target*measured < -.0001f && fabsf(measured) > .01f ? reverseMs_+lroundf(dt*1000) : 0;
        // Allow three expected pulses even at low speed/resolution; no fixed speed blind spot.
        if (quietMs_ >= config::encoderQuietMs && missingDistance_ >= 3*distancePerPulse)
            return "encoder_no_response";
        if (reverseMs_ >= 200) return "encoder_direction";
        return nullptr;
    }
    void reset() { quietMs_ = reverseMs_ = 0; missingDistance_ = 0; }
private:
    float missingDistance_ = 0;
    unsigned quietMs_ = 0, reverseMs_ = 0;
};
