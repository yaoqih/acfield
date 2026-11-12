#pragma once
#include <cstdint>
#include "config.h"

// A rolling pulse/time window, updated on every control tick. Raw counts stay
// untouched; normal telemetry and the optional PI use this speed estimate.
class EncoderSpeed {
public:
    float update(int32_t pulses, float dt, float distancePerPulse) {
        totalPulses_ += int64_t(pulses)-pulses_[next_];
        totalTime_ += double(dt)-time_[next_];
        pulses_[next_] = pulses;
        time_[next_] = dt;
        next_ = (next_+1)%config::encoderSpeedSamples;
        return float(totalPulses_)*distancePerPulse/totalTime_;
    }
    void reset() { *this = EncoderSpeed(); }
private:
    static_assert(config::encoderSpeedSamples > 0, "Encoder speed needs a nonempty window");
    int32_t pulses_[config::encoderSpeedSamples] = {};
    float time_[config::encoderSpeedSamples] = {};
    int64_t totalPulses_ = 0;
    double totalTime_ = 0;
    unsigned next_ = 0;
};
