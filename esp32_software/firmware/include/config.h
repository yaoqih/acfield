#pragma once
#ifndef ROBOT_ID
#define ROBOT_ID "car-01"
#endif
namespace config {
constexpr char robotId[] = ROBOT_ID;
constexpr char firmware[] = "0.2.1";
constexpr unsigned serverPort = 9999, localPort = 9998;
// V10/V11 nominal geometry. Verify effective rolling diameter on your chassis.
constexpr float wheelDiameter = 0.034f, trackWidth = 0.122f;
// Configured counts per OUTPUT shaft turn, single-channel RISING; verify on hardware.
// Set to zero to prevent activation during calibration; do not use quadrature x4 counts.
constexpr float pulsesPerTurn[2] = {300, 300};
constexpr int motorSign[2] = {1, 1}, encoderSign[2] = {1, 1};
// CHR-GM12-N20ABHL A12, 1:10: 1000 rpm rated speed, 2200 rpm no-load.
// Software cap is 1 m/s; validate chassis, driver, and stopping distance before raising it.
constexpr float maxV = 1.00f, maxOmega = 3.00f, maxWheelSpeed = 1.05f;
constexpr float acceleration = 0.30f;
constexpr float feedForward = 350, kp = 180, ki = 120;
constexpr unsigned controlMs = 10, telemetryMs = 25, batteryMs = 100;
constexpr float batteryStopV = 10.5f; // conservative initial 3S total; verify under load
constexpr unsigned batteryLowMs = 1000, encoderQuietMs = 800;
constexpr bool motorsEnabled = true;
inline bool calibrated() { return pulsesPerTurn[0] > 0 && pulsesPerTurn[1] > 0; }
}
