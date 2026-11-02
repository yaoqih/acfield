#pragma once
#include <cmath>
#include "config.h"

inline float clamp(float x, float low, float high) { return fmaxf(low, fminf(high, x)); }

class WheelControl {
public:
    float update(float goal, float measured, float dt) {
        target += clamp(goal-target, -config::acceleration*dt, config::acceleration*dt);
        float error = target-measured;
        float candidate = clamp(integral_+error*dt, -.5f, .5f);
        float base = config::feedForward*target+config::kp*error;
        float raw = base+config::ki*candidate;
        if ((raw <= 255 || error < 0) && (raw >= -255 || error > 0)) integral_ = candidate;
        // Coast when overspeed; avoid commanding an immediate reverse braking torque.
        return clamp(base+config::ki*integral_, target >= 0 ? 0.f : -255.f, target >= 0 ? 255.f : 0.f);
    }
    void reset() { target = integral_ = 0; }
    float target = 0;
private:
    float integral_ = 0;
};
