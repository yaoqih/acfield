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
            drive.update(v, omega, .16f, .2f);
            assert(near((drive.wheel[0]+drive.wheel[1])/2, v));
            assert(near((drive.wheel[1]-drive.wheel[0])/.16f, omega));
        }
    }
    DifferentialDrive drive;
    drive.update(.1f, -.3f, .16f, .2f);
    // A right diagonal must turn right from the very first control update.
    assert(drive.wheel[0] > drive.wheel[1] && drive.wheel[1] > 0);
    assert(near(drive.wheel[1]/drive.wheel[0], .076f/.124f));
    assert(near(drive.wheel[0], .124f) && near(drive.wheel[1], .076f));
    // A zero-wheel arc and then reversal each take effect in a single update.
    for (int leg = 0; leg < 2; ++leg) {
        const float v = leg ? -.1f : .024f, omega = .3f;
        const float leftGoal = v-omega*.08f, rightGoal = v+omega*.08f;
        drive.update(v, omega, .16f, .2f);
        assert(near(drive.wheel[0], leftGoal) && near(drive.wheel[1], rightGoal));
    }
    drive.reset();
    assert(drive.wheel[0] == 0 && drive.wheel[1] == 0);
    // Saturation scales the pair equally, preserving curvature.
    drive.update(.1f, -.3f, .16f, .08f);
    assert(near(drive.wheel[0], .08f));
    assert(near(drive.wheel[1]/drive.wheel[0], .076f/.124f));
    drive.update(-.1f, .3f, .16f, .08f);
    assert(near(drive.wheel[0], -.08f));
    assert(near(drive.wheel[1]/drive.wheel[0], .076f/.124f));
    drive.update(0, 0, .16f, .08f);
    assert(drive.wheel[0] == 0 && drive.wheel[1] == 0);
}
