#include "protocol.h"
#include "wheel_control.h"
#include "voltage_guard.h"
#include "encoder_guard.h"
#include <cassert>
#include <cstring>
#include <limits>
int main() {
    Protocol p(.1f, .3f);
    Protocol::Command c;
    c.session = "server-a"; c.seq = 1; c.ttl = 300; c.v = .1f;
    p.sent(0, 100);
    assert(!p.accept(c, 101)); // no implicit binding or implicit arm
    c.v = 0; c.stop = true; c.action = Protocol::Action::Stop;
    assert(p.accept(c, 102)); assert(!strcmp(p.state(), "disarmed"));
    c.seq = 2; c.action = Protocol::Action::Arm; assert(p.accept(c, 103));
    c.action = Protocol::Action::Drive; c.v = .1f; c.stop = false; c.seq = 3;
    assert(p.accept(c, 110));
    assert(!p.accept(c, 200)); // duplicates cannot renew deadline
    p.tick(410); assert(p.v == 0 && !strcmp(p.state(), "disarmed"));
    p.sent(1, 411); c.telemetry = 1; c.seq = 4;
    assert(!p.accept(c, 412)); // timeout requires explicit rearm, even for fresh motion
    c.v = 0; c.stop = true; c.action = Protocol::Action::Arm;
    assert(p.accept(c, 413));
    c.seq = 5; c.action = Protocol::Action::Drive; c.stop = false; c.v = .1f;
    c.telemetry = 999; assert(!p.accept(c, 414));
    c.telemetry = 1; c.v = std::numeric_limits<float>::quiet_NaN(); assert(!p.accept(c, 414));
    c.v = .11f; assert(!p.accept(c, 414));
    c.v = .1f; c.ttl = 501; assert(!p.accept(c, 414));
    c.ttl = 300; c.v = 0; c.stop = true; c.action = Protocol::Action::Stop;
    c.session = "server-b"; c.seq = 1; assert(p.accept(c, 415));
    c.session = "server-a"; c.seq = 99; assert(!p.accept(c, 416));
    c.session = "server-b"; c.seq = 2; c.action = Protocol::Action::Arm; c.telemetry = 5;
    p.sent(5, UINT32_MAX-50); assert(p.accept(c, UINT32_MAX-40));
    c.seq = 3; c.action = Protocol::Action::Drive; c.v = .1f; c.stop = false;
    assert(p.accept(c, UINT32_MAX-30));
    p.tick(270); assert(p.v == 0); // millis wrap
    p.linkLost(); assert(!p.hasAck && !strcmp(p.state(), "unbound"));
    p.sent(6, 300); c.telemetry = 6; c.seq = 4;
    c.v = 0; c.stop = true; c.action = Protocol::Action::Arm;
    assert(!p.accept(c, 301)); // reconnect requires stop, then explicit arm
    c.action = Protocol::Action::Stop; assert(p.accept(c, 302));
    c.seq = 5; c.action = Protocol::Action::Arm; assert(p.accept(c, 303));
    p.fault("encoder_no_response_left");
    c.seq = 6; assert(!p.accept(c, 304));
    c.action = Protocol::Action::Stop; assert(p.accept(c, 305));
    assert(!strcmp(p.state(), "fault")); // stop never clears a fault latch

    EncoderGuard encoder(true); // exercise thresholds with the optional guards enabled
    for (int i=0; i<74; ++i) assert(encoder.check(.1f, 0, .02f, .0002f, false) == nullptr);
    assert(!strcmp(encoder.check(.1f, 0, .02f, .0002f, false), "encoder_no_response"));
    encoder.reset();
    for (int i=0; i<49; ++i) assert(encoder.check(.1f, -.1f, .02f, .0002f, true) == nullptr);
    assert(!strcmp(encoder.check(.1f, -.1f, .02f, .0002f, true), "encoder_direction"));
    encoder.reset();
    // High measured speed alone must not latch a fault, in either direction.
    for (float direction : {1.f, -1.f}) {
        for (int i=0; i<100; ++i)
            assert(encoder.check(direction*.1f, direction*10*config::maxWheelSpeed, .02f, .0002f, true) == nullptr);
        encoder.reset();
    }
    encoder.reset();
    const float turning = config::maxOmega*config::trackWidth/2;
    for (int i=0; i<74; ++i) assert(encoder.check(turning, 0, .02f, .0002f, false) == nullptr);
    assert(!strcmp(encoder.check(turning, 0, .02f, .0002f, false), "encoder_no_response"));
    encoder.reset();
    // Coarse encoders at low speed need longer than 1500 ms to produce six pulses.
    for (int i=0; i<100; ++i) assert(encoder.check(.01f, 0, .02f, .01f, false) == nullptr);
    assert(encoder.check(.01f, .005f, .02f, .01f, true) == nullptr); // a pulse resets the window
    for (int i=0; i<100; ++i) assert(encoder.check(.01f, 0, .02f, .01f, false) == nullptr);
    encoder.reset();
    for (int i=0; i<301; ++i) encoder.check(.01f, 0, .02f, .01f, false);
    assert(!strcmp(encoder.check(.01f, 0, .02f, .01f, false), "encoder_no_response"));

    Protocol sessions(.1f, .3f);
    Protocol::Command binding;
    binding.action = Protocol::Action::Stop; binding.stop = true; binding.ttl = 100; binding.seq = 1;
    for (int i=0; i<100; ++i) {
        sessions.sent(i, i*50);
        binding.session = "session-"+std::to_string(i); binding.telemetry = i;
        assert(sessions.accept(binding, i*50+1));
        if (i) {
            auto replay = binding;
            replay.session = "session-"+std::to_string(i-1);
            replay.telemetry = i-1;
            assert(!sessions.accept(replay, i*50+2));
        }
    }
    sessions.linkLost();
    assert(!sessions.accept(binding, 5000)); // no rebinding from historical acknowledgments
    sessions.sent(100, 5000); binding.telemetry = 100;
    assert(sessions.accept(binding, 5001));
    sessions.sent(101, 5050);
    binding.session = "late-session"; binding.telemetry = 101;
    assert(!sessions.accept(binding, 5251)); // a new session also needs a fresh echo

    VoltageGuard voltage;
    assert(voltage.check(12.6f, 0) == nullptr);
    assert(voltage.check(10.4f, 100) == nullptr);
    assert(voltage.check(10.4f, 1099) == nullptr);
    assert(!strcmp(voltage.check(10.4f, 1100), "battery_low"));
    assert(voltage.check(11.f, 1101) == nullptr);
    assert(voltage.check(NAN, 1102) == nullptr);
    assert(!strcmp(voltage.warningCode(), "battery_sensor"));
    assert(voltage.check(12.4f, 1103) == nullptr);
    assert(voltage.warningCode() == nullptr); // recovery clears the advisory without reboot
    for (float invalid : {NAN, INFINITY, 0.f, 6.9f, 16.1f}) {
        assert(voltage.check(invalid, 1200) == nullptr);
        assert(!strcmp(voltage.warningCode(), "battery_sensor"));
    }
    assert(voltage.check(11.f, 1300) == nullptr);
    assert(voltage.warningCode() == nullptr);
    assert(voltage.check(10.4f, UINT32_MAX-100) == nullptr);
    assert(!strcmp(voltage.check(10.4f, 1000), "battery_low"));

    WheelControl wheel;
    assert(diagnosticPwm(0) == 0);
    assert(diagnosticPwm(1) == 255 && diagnosticPwm(-1) == -255);
    assert(diagnosticPwm(.05f) > 0 && diagnosticPwm(-.05f) < 0);
    float output = wheel.update(.1f, 0, .02f);
    assert(output > 0 && wheel.target == .1f); // target applies without acceleration limiting
    for (int i=0; i<100; ++i) wheel.update(.1f, 0, .02f);
    wheel.update(.05f, 0, .02f);
    assert(wheel.target == .05f);
    wheel.reset(); assert(wheel.target == 0);

    // Reproduce the real delayed telemetry: commands continue every 25 ms,
    // echoing the last received telemetry while incoming telemetry stalls 770 ms.
    for (uint32_t window : {200u, 1500u}) {
        Protocol delayed(255.f/350.f, .1f, window);
        Protocol::Command cmd;
        cmd.session = "diagnostic"; cmd.ttl = 500; cmd.stop = true;
        cmd.action = Protocol::Action::Stop; cmd.seq = 1;
        delayed.sent(0, 0);
        assert(delayed.accept(cmd, 1));
        cmd.action = Protocol::Action::Arm; ++cmd.seq;
        assert(delayed.accept(cmd, 2));
        cmd.action = Protocol::Action::Drive; cmd.stop = false; cmd.v = 255.f/350.f;
        for (uint32_t t = 25; t <= 775; t += 25) {
            // The device continues sending telemetry which the server hasn't received.
            delayed.sent(t/25, t);
            ++cmd.seq;
            const bool accepted = delayed.accept(cmd, t);
            assert(accepted == (window == 1500 || t <= 200));
            delayed.tick(t);
        }
        if (window == 200) {
            assert(!strcmp(delayed.state(), "disarmed"));
            assert(delayed.reason == "command_timeout" && delayed.motionEchoRejections > 0);
        } else {
            assert(!strcmp(delayed.state(), "armed") && delayed.motionEchoRejections == 0);
            // Freshness is relaxed only for motion; arm still needs a 200 ms echo.
            auto arm = cmd; arm.action = Protocol::Action::Arm; arm.v = 0; arm.stop = true; ++arm.seq;
            assert(!delayed.accept(arm, 776));
            assert(!delayed.accept(cmd, 776)); // duplicate does not renew TTL
            ++cmd.seq;
            assert(!delayed.accept(cmd, 1501));
            assert(delayed.motionEchoRejections == 1);
            delayed.tick(1501);
            assert(delayed.reason == "command_timeout");
        }
    }
}
