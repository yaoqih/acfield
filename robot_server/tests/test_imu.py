import math
import shutil
import subprocess
import time
from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.models import ImuSample, Telemetry, default_settings
from backend.state import Fleet, HEARTBEAT_TTL


def test_raw_imu_survives_telemetry_without_becoming_a_visual_pose():
    fleet = Fleet(default_settings(), "hardware")
    raw = dict(sampled_mono_us=1_250_000, sensor_ticks=42, age_ms=5, saturated=False,
               accel_m_s2=[0, 0, 9.80665], gyro_rad_s=[0, 0, -math.pi])
    common = dict(version=1, type="telemetry", robot_id="car-01", boot_id="imu-test")
    fleet.telemetry(Telemetry(**common, seq=1, imu=raw), ("127.0.0.1", 9998))
    robot = fleet.snapshot()["robots"][0]
    assert robot["imu"] == raw
    assert robot["theta"] is None and robot["acceleration"] is None
    fleet.robot("car-01").seen_at = time.monotonic()-HEARTBEAT_TTL-1
    assert fleet.snapshot()["robots"][0]["imu"] is None
    # Old firmware (or a failed sensor read) must clear the previous sample.
    fleet.telemetry(Telemetry(**common, seq=2), ("127.0.0.1", 9998))
    assert fleet.snapshot()["robots"][0]["imu"] is None


@pytest.mark.parametrize("bad", [[0, 0], [0, 0, float("nan")], [0, float("inf"), 0]])
def test_imu_rejects_incomplete_or_nonfinite_vectors(bad):
    with pytest.raises(ValidationError):
        ImuSample(sampled_mono_us=1, sensor_ticks=1, age_ms=0, saturated=False,
                  accel_m_s2=[0, 0, 9.8], gyro_rad_s=bad)


def test_imu_driver_units_probing_and_failed_reads(tmp_path):
    compiler = shutil.which("clang++") or shutil.which("g++")
    if not compiler:
        pytest.skip("C++ compiler required")
    # Exercise the actual driver with a register-level I2C fake, including a
    # device at the second possible address and a truncated sensor burst.
    (tmp_path/"Wire.h").write_text(r'''
#pragma once
#include <cstdint>
class FakeWire {
public:
    uint8_t registers[256] = {}, address = 0, reg = 0, position = 0;
    bool selecting = true, fail = false;
    void beginTransmission(uint8_t a) { address = a; selecting = true; }
    void write(uint8_t b) { if (selecting) { reg = b; selecting = false; } else registers[reg++] = b; }
    int endTransmission(bool = true) { return address == 0x6b && !fail ? 0 : 1; }
    int requestFrom(uint8_t, uint8_t count) { position = reg; return fail ? 0 : count; }
    int read() { return registers[position++]; }
};
static FakeWire Wire;
''')
    (tmp_path/"esp_timer.h").write_text("#pragma once\ninline long long esp_timer_get_time() { return 1234567; }\n")
    source = tmp_path/"imu_test.cpp"
    source.write_text(r'''
#include "imu.h"
#include <cassert>
#include <cmath>
void word(unsigned reg, int16_t v) {
    Wire.registers[reg] = uint16_t(v) & 255;
    Wire.registers[reg+1] = uint16_t(v) >> 8;
}
int main() {
    Imu missing;
    assert(!missing.begin() && !missing.sample().valid);
    Wire.registers[0] = 5;
    Imu imu;
    assert(imu.begin());
    Wire.registers[0x30] = 0x56; Wire.registers[0x31] = 0x34; Wire.registers[0x32] = 0x12;
    word(0x35, 4096); word(0x37, -4096); word(0x39, 0);
    word(0x3b, 32); word(0x3d, -32); word(0x3f, 32767);
    auto s = imu.sample();
    assert(s.valid && s.sampledMonoUs == 1234567 && s.sensorTicks == 0x123456);
    assert(std::fabs(s.accel[0]-9.80665f) < 0.0001f && std::fabs(s.accel[1]+9.80665f) < 0.0001f);
    assert(std::fabs(s.gyro[0]-0.0174532925f) < 0.000001f && std::fabs(s.gyro[1]+0.0174532925f) < 0.000001f);
    assert(s.saturated);
    word(0x3f, 0);
    assert(!imu.sample().saturated);
    Wire.fail = true;
    s = imu.sample();
    assert(!s.valid && s.sampledMonoUs == 0); // No stale reading presented as fresh.
}
''')
    firmware = Path(__file__).resolve().parents[2]/"esp32_software/firmware"
    binary = tmp_path/"imu-test"
    subprocess.run([compiler, "-std=c++11", "-Wall", "-Wextra", "-Werror", "-I", str(tmp_path),
                    "-I", str(firmware/"include"), str(source), "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
