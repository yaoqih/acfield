#pragma once
#include <cmath>

// Body frame: x forward, positive omega counterclockwise; index 0 left, 1 right.
class DifferentialDrive {
public:
    void update(float v, float omega, float track, float speedLimit, float acceleration, float dt) {
        float goal[2] = {v-omega*track/2, v+omega*track/2};
        const float peak = fmaxf(fabsf(goal[0]), fabsf(goal[1]));
        if (peak > speedLimit)
            for (auto& g : goal) g *= speedLimit/peak;
        const float change = fmaxf(fabsf(goal[0]-wheel[0]), fabsf(goal[1]-wheel[1]));
        const float fraction = change > 0 ? fminf(1, acceleration*dt/change) : 1;
        // A shared interpolation factor preserves the commanded wheel ratio from rest.
        // During transitions both wheels reach the new goal together, including zero crossings.
        for (unsigned i = 0; i < 2; ++i) wheel[i] += (goal[i]-wheel[i])*fraction;
    }
    void reset() { wheel[0] = wheel[1] = 0; }
    float wheel[2] = {};
};
