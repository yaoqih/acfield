#pragma once
#include <Wire.h>
#include <cmath>
#include "voltage_guard.h"

class Battery {
public:
    void begin() { Wire.begin(32, 33); Wire.setTimeOut(10); }
    const char* sample(uint32_t now) {
        uint16_t bus, shunt;
        valid = read(0x02, bus) && read(0x01, shunt) && (bus & 2);
        voltage = valid ? (bus >> 3)*.004f + int16_t(shunt)*.00001f : NAN;
        valid = valid && voltage >= 7 && voltage <= 16;
        const char* fault = guard_.check(valid ? voltage : NAN, now);
        warning = guard_.warningCode();
        return fault;
    }
    bool valid = false;
    float voltage = NAN;
    const char* warning = nullptr;
private:
    VoltageGuard guard_;
    bool read(uint8_t reg, uint16_t& value) {
        Wire.beginTransmission(0x42); Wire.write(reg);
        if (Wire.endTransmission(false) || Wire.requestFrom(uint8_t(0x42), uint8_t(2)) != 2) return false;
        value = uint16_t(Wire.read()) << 8; value |= Wire.read(); return true;
    }
};
