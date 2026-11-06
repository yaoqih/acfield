#include <cassert>
#include <cmath>
#include <limits>
#include "time_sync.h"
int main() {
    TimeSync clock;
    assert(!clock.ready(0));
    assert(clock.observe(100, 1000102, 1000103, 105));
    assert(clock.ready(105));
    assert(fabs(clock.now(105)-1000105) < .001);
    assert(!clock.observe(200, 1000200, 1000200, 300));
    assert(!clock.observe(NAN, 0, 0, 0));
    assert(!clock.observe(0, 0, std::numeric_limits<double>::infinity(), 1));
    assert(!clock.observe(20, 1000020, 1000021, 19));
    assert(!clock.observe(20, 1000021, 1000020, 25));
    // A new offset is slewed at 1ms/s, including a backwards correction.
    assert(clock.observe(200, 1000102, 1000103, 205));
    const double prior = clock.now(205);
    assert(fabs((clock.now(1205)-prior)-999) < .001);
    assert(!clock.ready(1205)); // correction exceeds the allowed uncertainty
    assert(!clock.ready(16000));
    clock.reset();
    assert(!clock.ready(16000));
}
