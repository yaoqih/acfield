#pragma once
#include <cmath>
#include <cstdint>

// Maps the device monotonic clock to server UTC. Synchronization never changes millis().
class TimeSync {
public:
    bool observe(double t1, double t2, double t3, double t4) {
        const double delay = (t4-t1)-(t3-t2);
        if (!std::isfinite(t1) || !std::isfinite(t4) || t4 < t1 || !std::isfinite(t2) || !std::isfinite(t3) || t3 < t2 || delay < -.1 || delay > 40) return false;
        const double rtt = fmax(0., delay); // tolerate epoch-millisecond serialization rounding
        const double candidate = ((t2-t1)+(t3-t4))/2;
        // Re-select the least congested path every 10 seconds.
        if (!valid_ || t4-bestAt_ > 10000 || rtt <= bestRtt_+1) {
            if (!valid_) offset_ = candidate;
            target_ = candidate; bestRtt_ = rtt; bestAt_ = t4;
            valid_ = true; observed_ = t4;
        }
        return true;
    }
    double now(double mono) {
        double limit = last_ ? (mono-last_)*.001 : 0;
        if (limit < 0) limit = 0;
        offset_ += fmax(-limit, fmin(limit, target_-offset_));
        last_ = mono;
        return mono+offset_;
    }
    double uncertainty(double mono) const {
        return bestRtt_/2 + fabs(target_-offset_) + fmax(0., mono-observed_)*.0001;
    }
    bool ready(double mono) const { return valid_ && mono-observed_ < 15000 && uncertainty(mono) <= 20; }
    void reset() { *this = TimeSync(); }
private:
    bool valid_ = false;
    double offset_ = 0, target_ = 0, bestRtt_ = 0, bestAt_ = 0, observed_ = 0, last_ = 0;
};
