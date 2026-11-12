#pragma once
#ifndef ROBOT_ID
#define ROBOT_ID "car-01"
#endif
namespace config {
constexpr char robotId[] = ROBOT_ID;
#ifdef ENCODER_DIAGNOSTIC
constexpr char firmware[] = "0.2.5-encoder-diagnostic";
constexpr bool encoderDiagnostic = true;
#else
constexpr char firmware[] = "0.2.8";
constexpr bool encoderDiagnostic = false;
#endif
constexpr unsigned serverPort = 9999, localPort = 9998;
// V10/V11 nominal geometry. Verify effective rolling diameter on your chassis.
constexpr float wheelDiameter = 0.034f, trackWidth = 0.122f;
// Configured counts per OUTPUT shaft turn, single-channel RISING; verify on hardware.
// Set to zero to prevent activation during calibration; do not use quadrature x4 counts.
// Same encoder as the previous 1:100 motor: 300 * 20 / 100 = 60 counts/turn.
constexpr float pulsesPerTurn[2] = {60, 60};
// Logical left/right -> physical driver and encoder channels (A=0, B=1).
// On this chassis B is the left wheel and A is the right wheel.
constexpr unsigned wheelChannels[2] = {1, 0};
constexpr int motorSign[2] = {-1, -1}, encoderSign[2] = {-1, -1};
// CHR-GM12-N20ABHL A12, 1:20: 500 rpm rated speed, 1100 rpm no-load.
// 500 rpm with 34 mm wheels is about 0.89 m/s; verify the loaded speed on hardware.
// Diagnostic v is a transport value: PWM / feedForward, not a speed estimate.
constexpr float feedForward = 350, kp = 180, ki = 120;
// Encoder feedback is currently observational only. Set true after feedback
// and PI calibration to restore normal closed-loop wheel-speed regulation.
constexpr bool motorClosedLoop = false;
constexpr float maxV = encoderDiagnostic ? 255.f/feedForward : 0.89f;
constexpr float maxOmega = encoderDiagnostic ? 0.10f : 6.00f;
constexpr float maxWheelSpeed = encoderDiagnostic ? 255.f/feedForward : 0.89f;
constexpr unsigned motionEchoMs = encoderDiagnostic ? 1500 : 200;
constexpr unsigned controlMs = 10, telemetryMs = 25, batteryMs = 100;
// Smooth pulse quantization without slowing the control or command loops.
constexpr unsigned encoderSpeedSamples = 5;
// Encoder fault stops remain disabled. Open-loop drive bypasses them as well.
constexpr bool encoderGuardsEnabled = false;
constexpr unsigned encoderQuietMs = 1500, encoderReverseMs = 1000;
constexpr unsigned encoderEvidencePulses = 6;
constexpr float encoderReverseMinSpeed = .05f;
constexpr float batteryStopV = 10.5f; // conservative initial 3S total; verify under load
constexpr unsigned batteryLowMs = 1000;
constexpr bool motorsEnabled = true;
inline bool calibrated() { return pulsesPerTurn[0] > 0 && pulsesPerTurn[1] > 0; }
}
