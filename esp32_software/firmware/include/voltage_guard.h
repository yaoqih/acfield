#pragma once
#include <cmath>
#include <cstdint>
#include "config.h"

class VoltageGuard {
public:
    const char* check(float voltage, uint32_t now) {
        sensorWarning_ = !std::isfinite(voltage) || voltage < 7 || voltage > 16;
        // Missing readings cannot establish continuous undervoltage.
        if (sensorWarning_) { low_ = false; return nullptr; }
        if (voltage < config::batteryStopV) {
            if (!low_) { low_ = true; lowAt_ = now; }
            if (uint32_t(now-lowAt_) >= config::batteryLowMs) return "battery_low";
        } else low_ = false;
        return nullptr;
    }
    const char* warningCode() const { return sensorWarning_ ? "battery_sensor" : nullptr; }
private:
    bool sensorWarning_ = false;
    bool low_ = false;
    uint32_t lowAt_ = 0;
};
