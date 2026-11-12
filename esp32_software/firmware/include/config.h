#pragma once
#ifndef ROBOT_ID
#define ROBOT_ID "car-01"
#endif
namespace config {
constexpr char robotId[] = ROBOT_ID;
constexpr char firmware[] = "0.2.3";
constexpr unsigned serverPort = 9999, localPort = 9998;
// V10/V11 nominal geometry. Verify effective rolling diameter on your chassis.
constexpr float wheelDiameter = 0.034f, trackWidth = 0.122f;
// Configured counts per OUTPUT shaft turn, single-channel RISING; verify on hardware.
// Set to zero to prevent activation during calibration; do not use quadrature x4 counts.
// Same encoder as the previous 1:100 motor: 300 * 20 / 100 = 60 counts/turn.
constexpr float pulsesPerTurn[2] = {60, 60};
constexpr int motorSign[2] = {1, 1}, encoderSign[2] = {1, 1};
// CHR-GM12-N20ABHL A12, 1:20: 500 rpm rated speed, 1100 rpm no-load.
// 500 rpm with 34 mm wheels is about 0.89 m/s; verify the loaded speed on hardware.
constexpr float maxV = 0.89f, maxOmega = 3.00f, maxWheelSpeed = 0.89f;
constexpr float feedForward = 350, kp = 180, ki = 120;
constexpr unsigned controlMs = 10, telemetryMs = 25, batteryMs = 100;
constexpr float batteryStopV = 10.5f; // conservative initial 3S total; verify under load
constexpr unsigned batteryLowMs = 1000, encoderQuietMs = 800;
constexpr bool motorsEnabled = true;
inline bool calibrated() { return pulsesPerTurn[0] > 0 && pulsesPerTurn[1] > 0; }
}
