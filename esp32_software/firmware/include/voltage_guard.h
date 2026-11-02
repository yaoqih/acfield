#pragma once
#include <cmath>
#include <cstdint>
#include "config.h"

class VoltageGuard {
public:
    const char* check(float voltage, uint32_t now) {
        if (!std::isfinite(voltage) || voltage < 7 || voltage > 16) return "battery_sensor";
        if (voltage < config::batteryStopV) {
            if (!low_) { low_ = true; lowAt_ = now; }
            if (uint32_t(now-lowAt_) >= config::batteryLowMs) return "battery_low";
        } else low_ = false;
        return nullptr;
    }
private:
    bool low_ = false;
    uint32_t lowAt_ = 0;
};
