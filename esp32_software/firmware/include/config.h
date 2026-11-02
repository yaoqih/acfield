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
// Unknown until measured: counts per OUTPUT shaft turn, single-channel RISING.
// Zero deliberately prevents motor activation; never copy quadrature x4 counts here.
constexpr float pulsesPerTurn[2] = {0, 0};
constexpr int motorSign[2] = {1, 1}, encoderSign[2] = {1, 1};
constexpr float maxV = 0.10f, maxOmega = 0.30f, maxWheelSpeed = 0.13f;
constexpr float acceleration = 0.30f;
constexpr float feedForward = 350, kp = 180, ki = 120;
constexpr unsigned controlMs = 20, telemetryMs = 50, batteryMs = 100;
constexpr float batteryStopV = 10.5f; // conservative initial 3S total; verify under load
constexpr unsigned batteryLowMs = 1000, encoderQuietMs = 800;
constexpr bool motorsEnabled = false;
inline bool calibrated() { return pulsesPerTurn[0] > 0 && pulsesPerTurn[1] > 0; }
}
