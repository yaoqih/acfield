#pragma once
#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <cstdint>
#define IRAM_ATTR
#define OUTPUT 1
#define INPUT 0
#define LOW 0
#define RISING 1
#define PI 3.14159265358979323846
using portMUX_TYPE = int;
#define portMUX_INITIALIZER_UNLOCKED 0
inline void portENTER_CRITICAL_ISR(portMUX_TYPE*) {}
inline void portEXIT_CRITICAL_ISR(portMUX_TYPE*) {}
inline void portENTER_CRITICAL(portMUX_TYPE*) {}
inline void portEXIT_CRITICAL(portMUX_TYPE*) {}
namespace fakeArduino {
using Interrupt = void (*)();
inline Interrupt* interrupts() { static Interrupt handlers[40] = {}; return handlers; }
inline int* levels() { static int pins[40] = {}; return pins; }
inline int* duties() { static int channels[2] = {}; return channels; }
inline void pulse(int clockPin, int directionPin, int direction) {
    levels()[directionPin] = direction;
    interrupts()[clockPin]();
}
}
inline int digitalRead(int pin) { return fakeArduino::levels()[pin]; }
inline void pinMode(int, int) {}
inline void digitalWrite(int pin, int value) { fakeArduino::levels()[pin] = value; }
inline void ledcSetup(int, int, int) {}
inline void ledcAttachPin(int, int) {}
inline void ledcWrite(int channel, int value) { fakeArduino::duties()[channel] = value; }
inline void attachInterrupt(int pin, void (*handler)(), int) { fakeArduino::interrupts()[pin] = handler; }
template <typename T> T constrain(T value, T low, T high) { return std::max(low, std::min(high, value)); }
