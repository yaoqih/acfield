#pragma once
#include <cmath>

// Body frame: x forward, positive omega counterclockwise; index 0 left, 1 right.
class DifferentialDrive {
public:
    void update(float v, float omega, float track, float speedLimit) {
        float goal[2] = {v-omega*track/2, v+omega*track/2};
        const float peak = fmaxf(fabsf(goal[0]), fabsf(goal[1]));
        if (peak > speedLimit)
            for (auto& g : goal) g *= speedLimit/peak;
        // Apply the speed-limited targets on this control update, including reversals.
        for (unsigned i = 0; i < 2; ++i) wheel[i] = goal[i];
    }
    void reset() { wheel[0] = wheel[1] = 0; }
    float wheel[2] = {};
};
