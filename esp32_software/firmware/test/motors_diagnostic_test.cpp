#include "motors.h"
#include <cassert>
#include <cstring>
#include <cmath>

void pulseWheel(unsigned wheel, int level) {
    const int clock[] = {34, 16}, direction[] = {35, 27};
    const unsigned channel = config::wheelChannels[wheel];
    fakeArduino::pulse(clock[channel], direction[channel], level);
}

int main() {
    static_assert(config::wheelChannels[0] == 1 && config::wheelChannels[1] == 0,
                  "This chassis has B on the left and A on the right");
    Motors mapping;
    mapping.begin();
    // Positive yaw means left: physical A/right must run faster than B/left.
    mapping.update(.2f, .05f, .01f);
    assert(fakeArduino::duties()[0] > fakeArduino::duties()[1]);
    assert(fakeArduino::levels()[21] == (config::motorSign[1] < 0));
    assert(fakeArduino::levels()[22] == (config::motorSign[0] < 0));
    // A pulse on each physical encoder must appear on the same logical wheel.
    fakeArduino::pulse(34, 35, 1);
    mapping.update(0, 0, .01f);
    assert(mapping.encoder[0] == 0 && mapping.encoder[1] == 1);
    fakeArduino::pulse(16, 27, 0);
    mapping.update(0, 0, .01f);
    assert(mapping.encoder[0] == -1 && mapping.encoder[1] == 1);
    mapping.stop();

    Motors feedback;
    feedback.begin();
    const float distancePerPulse = PI*config::wheelDiameter/config::pulsesPerTurn[0];
    for (int i = 0; i < 100; ++i) {
        // Same mean speed, with pulse bursts instead of evenly spaced edges.
        const int pulses = i%5 == 0 ? 5 : 0;
        for (int n = 0; n < pulses; ++n) {
            pulseWheel(0, config::encoderSign[0] > 0);
            pulseWheel(1, config::encoderSign[1] > 0);
        }
        const float requested = i%2 == 0 ? .2f : .3f;
        feedback.update(requested, 0, .01f);
        assert(!feedback.fault);
        assert(feedback.target[0] == requested && feedback.target[1] == requested);
        if (config::encoderDiagnostic || !config::motorClosedLoop) {
            assert(std::fabs(feedback.pwm[0]-requested*config::feedForward) < .001f);
            assert(std::fabs(feedback.pwm[1]-requested*config::feedForward) < .001f);
        }
        assert(feedback.encoder[0] == config::encoderSign[0]*5*(i/5+1)); // raw counts stay exact
        const float expected = config::encoderDiagnostic ? pulses*distancePerPulse/.01f : distancePerPulse/.01f;
        if (i >= 4) {
            assert(std::fabs(feedback.speed[0]-expected) < .00001f);
            assert(std::fabs(feedback.speed[1]-expected) < .00001f);
        }
    }
    feedback.stop();
    assert(feedback.pwm[0] == 0 && feedback.pwm[1] == 0);

    if (!config::encoderDiagnostic && config::motorClosedLoop) {
        // Equal wheel targets with asymmetric encoder speeds must produce
        // more drive on the slower wheel, in both forward and reverse.
        for (float direction : {1.f, -1.f}) {
            Motors regulated;
            regulated.begin();
            for (int i = 0; i < 20; ++i) {
                for (unsigned wheel = 0; wheel < 2; ++wheel)
                    for (int n = 0; n < (wheel == 0 ? 2 : 4); ++n)
                        pulseWheel(wheel, direction*config::encoderSign[wheel] > 0);
                regulated.update(direction*.3f, 0, .01f);
            }
            assert(direction*regulated.speed[0] < direction*regulated.speed[1]);
            assert(std::fabs(regulated.pwm[0]) > std::fabs(regulated.pwm[1]));
            assert(!regulated.fault);
            regulated.stop();
        }
    }

    Motors motors;
    motors.begin();
    // Persistent missing feedback must not stop either build when guards are disabled.
    for (int i = 0; i < 120; ++i) motors.update(.1f, 0, .01f);
    assert(!motors.fault && motors.pwm[0] > 0 && motors.pwm[1] > 0);
    for (int i = 0; i < 80; ++i) motors.update(.1f, 0, .01f);
    assert(motors.encoder[0] == 0 && motors.encoder[1] == 0);
    assert(!motors.fault && motors.pwm[0] > 0 && motors.pwm[1] > 0);
    // Reversed feedback for both wheels must likewise leave motion available.
    for (float direction : {1.f, -1.f}) {
        motors.stop();
        for (int i = 0; i < 300; ++i) {
            pulseWheel(0, direction*config::encoderSign[0] < 0);
            pulseWheel(1, direction*config::encoderSign[1] < 0);
            motors.update(direction*.1f, 0, .01f);
            assert(!motors.fault);
            assert(direction*motors.pwm[0] > 0 && direction*motors.pwm[1] > 0);
        }
        assert(direction*motors.speed[0] < 0 && direction*motors.speed[1] < 0);
    }
    if (config::encoderDiagnostic) {
        // The diagnostic page maps these PWM inputs through the existing v protocol.
        for (float requested : {18.f, 100.f, 255.f, 0.f, -10.f, -255.f}) {
            motors.update(requested/350.f, 0, .01f);
            assert(std::fabs(motors.pwm[0]-requested) < .001f);
            assert(std::fabs(motors.pwm[1]-requested) < .001f);
        }
    }
    if (!config::encoderDiagnostic && !config::motorClosedLoop) {
        // Hold an unchanged command while injecting large, asymmetric forward
        // and reverse pulse bursts. Raw/smoothed telemetry may change freely;
        // PWM must remain constant and retain both wheels' steering targets.
        motors.stop();
        const float goalV = .2f, goalOmega = -.5f;
        const float left = goalV-goalOmega*config::trackWidth/2;
        const float right = goalV+goalOmega*config::trackWidth/2;
        for (int i = 0; i < 500; ++i) {
            for (int pulse = 0; pulse < (i%4 == 0 ? 80 : 0); ++pulse)
                pulseWheel(0, i%8 == 0);
            for (int pulse = 0; pulse < (i%3 == 0 ? 30 : 0); ++pulse)
                pulseWheel(1, i%6 == 0);
            motors.update(goalV, goalOmega, .01f);
            assert(!motors.fault);
            assert(std::fabs(motors.pwm[0]-left*config::feedForward) < .001f);
            assert(std::fabs(motors.pwm[1]-right*config::feedForward) < .001f);
        }
        assert(motors.encoder[0] != 0 || motors.encoder[1] != 0);
        // Joint saturation preserves the ratio in both driving directions.
        for (float direction : {1.f, -1.f}) {
            motors.update(direction*.8f, -direction*2.f, .01f);
            assert(std::fabs(motors.pwm[0]-direction*255) < .001f);
            assert(std::fabs(motors.pwm[1]/motors.pwm[0]-motors.target[1]/motors.target[0]) < .00001f);
        }
        // Zero and reversal act on the next 10 ms tick, with no feedback tail.
        motors.update(0, 0, .01f);
        assert(motors.pwm[0] == 0 && motors.pwm[1] == 0);
        motors.update(-.1f, 0, .01f);
        assert(std::fabs(motors.pwm[0]+35) < .001f && std::fabs(motors.pwm[1]+35) < .001f);
        motors.stop();
        assert(motors.pwm[0] == 0 && motors.pwm[1] == 0);
        motors.update(0, 0, .01f);
        assert(motors.pwm[0] == 0 && motors.pwm[1] == 0);
    }
    motors.stop();
    assert(motors.pwm[0] == 0 && motors.pwm[1] == 0);
    motors.update(.1f, 0, .11f);
    assert(motors.fault && !std::strcmp(motors.fault, "control_overrun"));
    assert(motors.pwm[0] == 0 && motors.pwm[1] == 0);
}
