#pragma once
#include <array>
#include <cmath>
#include <cstdint>
#include <string>

class Protocol {
public:
    enum class Action { Stop, Arm, Drive };
    struct Command {
        std::string session;
        uint64_t seq = 0, telemetry = 0;
        float v = 0, omega = 0;
        uint32_t ttl = 0;
        bool stop = false;
        Action action = Action::Drive;
    };
    Protocol(float maxV, float maxOmega, uint32_t motionEchoMs = 200)
        : maxV_(maxV), maxOmega_(maxOmega), motionEchoMs_(motionEchoMs) {}
    void sent(uint64_t seq, uint32_t now) {
        auto& stamp = history_[cursor_++ % history_.size()];
        stamp.seq = seq; stamp.time = now; stamp.valid = true;
        lastSent_ = seq;
    }
    bool accept(const Command& c, uint32_t now, uint32_t age = 0) {
        if (c.session.empty() || c.session.size() > 64 ||
            !std::isfinite(c.v) || !std::isfinite(c.omega) ||
            c.ttl < 100 || c.ttl > 500 || age >= c.ttl) return false;
        const bool zero = c.v == 0 && c.omega == 0;
        if (c.stop != zero) return false;
        if (c.action != Action::Drive && !zero) return false;
        if (c.action == Action::Drive &&
            (std::fabs(c.v) > maxV_ || std::fabs(c.omega) > maxOmega_)) return false;
        if (c.session != session || awaitingStop_) {
            if (c.action != Action::Stop) return false;
            if (!fresh(c.telemetry, now) || (hasBinding_ && c.telemetry <= bindingFloor_)) return false;
            // Old-session packets cannot echo telemetry sent after the latest binding.
            bindingFloor_ = lastSent_;
            hasBinding_ = true;
            session = c.session;
            hasAck = false;
        }
        if (hasAck && c.seq <= ackSeq) return false;
        if (c.action != Action::Stop && (awaitingStop_ || !fault_.empty())) return false;
        if (c.action == Action::Arm && !fresh(c.telemetry, now)) return false;
        if (c.action == Action::Drive && !zero && !fresh(c.telemetry, now, motionEchoMs_)) {
            ++motionEchoRejections;
            return false;
        }
        if (c.action == Action::Drive && !armed_) return false;
        if (c.action == Action::Stop) {
            disarm("server_stop"); awaitingStop_ = false;
        } else if (c.action == Action::Arm) {
            armed_ = true; reason = "armed"; v = omega = 0; moving_ = false;
        } else {
            v = c.v; omega = c.omega;
            moving_ = !zero;
            reason = zero ? "idle" : "driving";
        }
        ackSeq = c.seq; hasAck = true;
        received_ = now-age; ttl_ = c.ttl;
        return true;
    }
    void tick(uint32_t now) {
        if (moving_ && uint32_t(now-received_) >= ttl_) disarm("command_timeout");
    }
    void disarm(const char* why) { v = omega = 0; armed_ = moving_ = false; reason = why; }
    void linkLost() {
        disarm("link_lost"); awaitingStop_ = true; hasAck = false;
        for (auto& h : history_) h.valid = false;
    }
    void fault(const char* code) {
        if (fault_.empty()) fault_ = code;
        disarm(fault_.c_str());
    }
    const char* faultCode() const { return fault_.empty() ? nullptr : fault_.c_str(); }
    const char* state() const {
        return !fault_.empty() ? "fault" : awaitingStop_ ? "unbound" : armed_ ? "armed" : "disarmed";
    }
    std::string session, reason = "boot";
    uint64_t ackSeq = 0;
    uint32_t motionEchoRejections = 0;
    bool hasAck = false;
    float v = 0, omega = 0;
private:
    struct Stamp { uint64_t seq = 0; uint32_t time = 0; bool valid = false; };
    std::array<Stamp, 128> history_{};
    bool fresh(uint64_t seq, uint32_t now, uint32_t maxAge = 200) const {
        for (const auto& h : history_)
            if (h.valid && h.seq == seq && uint32_t(now-h.time) <= maxAge) return true;
        return false;
    }
    size_t cursor_ = 0;
    uint64_t lastSent_ = 0, bindingFloor_ = 0;
    uint32_t received_ = 0, ttl_ = 0;
    float maxV_, maxOmega_;
    uint32_t motionEchoMs_;
    bool awaitingStop_ = true, armed_ = false, moving_ = false, hasBinding_ = false;
    std::string fault_;
};
