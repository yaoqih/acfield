#include "encoder_speed.h"
#include "encoder_guard.h"
#include <cassert>
#include <cmath>
#include <cstring>
#include <initializer_list>

int main() {
    EncoderSpeed speed;
    // Five pulses arriving together should settle to the same speed as one
    // pulse per tick, without slowing the 10 ms update cadence.
    for (int i = 0; i < 100; ++i) {
        const float measured = speed.update(i%5 == 0 ? 5 : 0, .01f, .001f);
        if (i >= 4) assert(std::fabs(measured-.1f) < .000001f);
    }
    // A complete reversal reaches its new value within five control ticks.
    float reversed = 0;
    for (int i = 0; i < 5; ++i) reversed = speed.update(-1, .01f, .001f);
    assert(std::fabs(reversed+.1f) < .000001f);
    // Use the real elapsed time, rather than averaging per-tick velocities.
    speed.reset();
    speed.update(1, .01f, .001f);
    assert(std::fabs(speed.update(1, .02f, .001f)-2.f/30) < .000001f);
    assert(std::fabs(speed.update(1, .01f, -.001f)+.075f) < .000001f);
    speed.reset();
    assert(speed.update(0, .01f, .001f) == 0);

    // Default builds must tolerate persistent missing and reversed feedback.
    assert(!config::encoderGuardsEnabled);
    EncoderGuard disabled;
    for (float direction : {1.f, -1.f}) {
        for (int i = 0; i < 1000; ++i)
            assert(!disabled.check(direction*.1f, 0, .01f, .001f, false));
        disabled.reset();
        for (int i = 0; i < 1000; ++i)
            assert(!disabled.check(direction*.1f, -direction*.1f, .01f, .001f, true));
        disabled.reset();
    }

    EncoderGuard guard(true); // retain coverage for explicitly re-enabling the guards
    // Repeated brief reversals reset on recovery and never accumulate a latch.
    for (int i = 0; i < 1000; ++i) {
        const float measured = i%100 < 80 ? -.1f : .1f;
        assert(!guard.check(.1f, measured, .01f, .001f, true));
    }
    // Low-amplitude sign jitter does not latch even when it lasts seconds.
    guard.reset();
    for (int i = 0; i < 300; ++i)
        assert(!guard.check(.1f, -.04f, .01f, .001f, true));

    // Sparse reverse pulses still indicate a sustained wrong direction. Using
    // raw per-tick speed here would reset the timer between every pulse.
    guard.reset();
    speed.reset();
    bool reverseDetected = false;
    for (int i = 0; i < 150; ++i) {
        const int pulses = i%3 == 0 ? -3 : 0;
        const float measured = speed.update(pulses, .01f, .001f);
        const char* fault = guard.check(.1f, measured, .01f, .001f, pulses != 0);
        if (fault) {
            assert(!std::strcmp(fault, "encoder_direction"));
            reverseDetected = true;
            break;
        }
    }
    assert(reverseDetected);

    // Real pulse absence, rather than the smoothed speed's trailing samples,
    // determines the 1.5 s timeout. A single pulse restarts that interval.
    guard.reset();
    for (int i = 0; i < 149; ++i)
        assert(!guard.check(.1f, .1f, .01f, .001f, false));
    assert(!guard.check(.1f, .1f, .01f, .001f, true));
    for (int i = 0; i < 149; ++i)
        assert(!guard.check(.1f, .1f, .01f, .001f, false));
    const char* silence = guard.check(.1f, .1f, .01f, .001f, false);
    assert(silence && !std::strcmp(silence, "encoder_no_response"));

    // Coarse resolution also requires six pulses' distance of reverse evidence,
    // even after the one-second threshold has elapsed.
    guard.reset();
    for (int i = 0; i < 190; ++i)
        assert(!guard.check(.1f, -.06f, .01f, .02f, true));
    bool distanceReached = false;
    for (int i = 0; i < 20; ++i) {
        if (const char* fault = guard.check(.1f, -.06f, .01f, .02f, true)) {
            assert(!std::strcmp(fault, "encoder_direction"));
            distanceReached = true;
            break;
        }
    }
    assert(distanceReached);
}
