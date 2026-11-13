#pragma once
#include <Wire.h>
#include <esp_timer.h>
#include <cstdint>
#include <initializer_list>

// Raw QMI8658C diagnostic data, in the SENSOR frame; no heading or bias correction.
// Registers/scales verified against Waveshare's General Driver / UGV01 demo:
// https://files.waveshare.com/upload/0/0c/UGV01_BASE.zip (IMU_QMI8658.{h,cpp}).
struct ImuSample {
    uint64_t sampledMonoUs = 0;
    uint32_t sensorTicks = 0;
    float accel[3] = {}, gyro[3] = {};
    bool valid = false, saturated = false;
};

class Imu {
public:
    // Wire is initialized by Battery. Use only before tasks start or from the
    // shared sensor task, never concurrently with INA219 transactions.
    bool begin() {
        ready_ = false;
        for (uint8_t address : {uint8_t(0x6a), uint8_t(0x6b)}) {
            address_ = address;
            uint8_t id = 0;
            if (read(0x00, &id, 1) && id == 0x05) {
                // Auto increment, sensors disabled while configuring, +/-8g,
                // +/-1024 degrees/s, 125 Hz, no digital LPF, synchronous output.
                ready_ = write(0x08, 0x00) && write(0x02, 0x60) &&
                         write(0x03, 0x26) && write(0x04, 0x56) &&
                         write(0x06, 0x00) && write(0x08, 0x83);
                uint8_t acc = 0, gyro = 0;
                ready_ = ready_ && read(0x03, &acc, 1) && read(0x04, &gyro, 1) &&
                         acc == 0x26 && gyro == 0x56;
                return ready_;
            }
        }
        return false;
    }

    ImuSample sample() {
        ImuSample result;
        if (!ready_) return result;
        // Read timestamp, temperature, acceleration and gyro in one burst.
        uint8_t data[17];
        if (!read(0x30, data, sizeof(data))) return result;
        result.sampledMonoUs = esp_timer_get_time();
        result.sensorTicks = uint32_t(data[0]) | uint32_t(data[1]) << 8 | uint32_t(data[2]) << 16;
        for (unsigned axis = 0; axis < 3; ++axis) {
            const int16_t a = decode(data + 5 + 2*axis);
            const int16_t g = decode(data + 11 + 2*axis);
            result.accel[axis] = a * (9.80665f / 4096.f);
            result.gyro[axis] = g * (0.017453292519943295f / 32.f);
            result.saturated |= a >= 32760 || a <= -32760 || g >= 32760 || g <= -32760;
        }
        result.valid = true;
        return result;
    }

private:
    uint8_t address_ = 0;
    bool ready_ = false;
    static int16_t decode(const uint8_t* data) {
        return int16_t(uint16_t(data[0]) | uint16_t(data[1]) << 8);
    }
    bool write(uint8_t reg, uint8_t value) {
        Wire.beginTransmission(address_); Wire.write(reg); Wire.write(value);
        return Wire.endTransmission() == 0;
    }
    bool read(uint8_t reg, uint8_t* data, uint8_t size) {
        Wire.beginTransmission(address_); Wire.write(reg);
        if (Wire.endTransmission(false) || Wire.requestFrom(address_, size) != size) return false;
        for (uint8_t i = 0; i < size; ++i) data[i] = Wire.read();
        return true;
    }
};
