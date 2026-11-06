#pragma once
#include <array>
#include "protocol.h"

// Uses only device monotonic time after admission. UTC corrections cannot move a queued deadline.
class CommandScheduler {
public:
    bool enqueue(const Protocol::Command& command, uint32_t now, uint32_t delay, const Protocol& protocol) {
        if (delay > 150 || delay >= command.ttl || command.session != protocol.session ||
            (protocol.hasAck && command.seq <= protocol.ackSeq)) return false;
        for (const auto& item : items_)
            if (item.valid && item.command.session == command.session && item.command.seq == command.seq) return false;
        for (auto& item : items_) {
            if (!item.valid) {
                item.command = command; item.received = now; item.due = now+delay; item.valid = true;
                return true;
            }
        }
        return false;
    }
    bool apply(Protocol& protocol, uint32_t now) {
        bool changed = false;
        while (true) {
            Item* next = nullptr;
            for (auto& item : items_) {
                if (item.valid && int32_t(now-item.due) >= 0 && (!next || int32_t(item.due-next->due) < 0))
                    next = &item;
            }
            if (!next) break;
            next->valid = false;
            if (uint32_t(now-next->due) <= 20 && protocol.accept(next->command, now, now-next->received)) changed = true;
        }
        return changed;
    }
    void clear() { for (auto& item : items_) item.valid = false; }
private:
    struct Item { Protocol::Command command; uint32_t received = 0, due = 0; bool valid = false; };
    std::array<Item, 8> items_{};
};
