#pragma once
#include <cmath>
#include "config.h"

class EncoderGuard {
public:
    explicit EncoderGuard(bool enabled = config::encoderGuardsEnabled) : enabled_(enabled) {}
    const char* check(float target, float measured, float dt, float distancePerPulse, bool pulseObserved) {
        if (!enabled_) return nullptr;
        if (target != 0 && !pulseObserved) {
            quietMs_ += lroundf(dt*1000);
            missingDistance_ += fabsf(target)*dt;
        } else { quietMs_ = 0; missingDistance_ = 0; }
        if (target*measured < -.0001f && fabsf(measured) > config::encoderReverseMinSpeed) {
            reverseMs_ += lroundf(dt*1000);
            reverseDistance_ += fabsf(measured)*dt;
        } else { reverseMs_ = 0; reverseDistance_ = 0; }
        // Require time plus enough pulse evidence; short gaps and sign jitter
        // must not latch a fault. Use raw pulse presence for silence so speed
        // smoothing cannot extend the no-pulse timeout.
        if (quietMs_ >= config::encoderQuietMs && missingDistance_ >= config::encoderEvidencePulses*distancePerPulse)
            return "encoder_no_response";
        if (reverseMs_ >= config::encoderReverseMs && reverseDistance_ >= config::encoderEvidencePulses*distancePerPulse)
            return "encoder_direction";
        return nullptr;
    }
    void reset() { quietMs_ = reverseMs_ = 0; missingDistance_ = reverseDistance_ = 0; }
private:
    const bool enabled_;
    float missingDistance_ = 0, reverseDistance_ = 0;
    unsigned quietMs_ = 0, reverseMs_ = 0;
};
