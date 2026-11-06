#include "differential_drive.h"
#include <cassert>
#include <cmath>
#include <initializer_list>

static bool near(float a, float b) { return fabsf(a-b) < 1e-6f; }

int main() {
    // Body-frame commands: forward, reverse, both spins and all four diagonals.
    for (float v : {-.1f, 0.f, .1f}) {
        for (float omega : {-.3f, 0.f, .3f}) {
            DifferentialDrive drive;
            for (int i = 0; i < 200; ++i) drive.update(v, omega, .16f, .2f, .1f, .01f);
            assert(near((drive.wheel[0]+drive.wheel[1])/2, v));
            assert(near((drive.wheel[1]-drive.wheel[0])/.16f, omega));
        }
    }
    DifferentialDrive drive;
    drive.update(.1f, -.3f, .16f, .2f, .1f, .01f);
    // A right diagonal must turn right from the very first control update.
    assert(drive.wheel[0] > drive.wheel[1] && drive.wheel[1] > 0);
    assert(near(drive.wheel[1]/drive.wheel[0], .076f/.124f));
    for (int i = 0; i < 200; ++i) drive.update(.1f, -.3f, .16f, .2f, .1f, .01f);
    // Transition through a zero-wheel arc and then reverse: no per-wheel jumps.
    for (int leg = 0; leg < 2; ++leg) {
        const float v = leg ? -.1f : .024f, omega = .3f;
        const float leftGoal = v-omega*.08f, rightGoal = v+omega*.08f;
        for (int i = 0; i < 300; ++i) {
            const float left = drive.wheel[0], right = drive.wheel[1];
            drive.update(v, omega, .16f, .2f, .1f, .01f);
            assert(fabsf(drive.wheel[0]-left) <= .001001f);
            assert(fabsf(drive.wheel[1]-right) <= .001001f);
            // Shared progression reaches the new pair of goals together.
            assert(fabsf((drive.wheel[0]-left)*(rightGoal-right)-(drive.wheel[1]-right)*(leftGoal-left)) < 1e-8f);
        }
        assert(near(drive.wheel[0], leftGoal) && near(drive.wheel[1], rightGoal));
    }
    drive.reset();
    assert(drive.wheel[0] == 0 && drive.wheel[1] == 0);
    // Saturation scales the pair equally, preserving curvature.
    for (int i = 0; i < 300; ++i) drive.update(.1f, -.3f, .16f, .08f, .1f, .01f);
    assert(near(drive.wheel[0], .08f));
    assert(near(drive.wheel[1]/drive.wheel[0], .076f/.124f));
}
