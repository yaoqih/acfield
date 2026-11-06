#include "command_scheduler.h"
#include <cassert>
#include <cstring>

static Protocol::Command setup(Protocol& protocol, uint32_t now) {
    protocol.sent(1, now);
    Protocol::Command c;
    c.session = "server"; c.seq = 1; c.telemetry = 1; c.ttl = 100;
    c.action = Protocol::Action::Stop; c.stop = true;
    assert(protocol.accept(c, now));
    c.seq = 2; c.action = Protocol::Action::Arm;
    assert(protocol.accept(c, now));
    c.seq = 3; c.action = Protocol::Action::Drive; c.stop = false; c.v = .05f;
    return c;
}

int main() {
    {
        Protocol p(.1f, .3f); auto c = setup(p, 100);
        CommandScheduler queue;
        // Legal TTL=100 survives a 60ms buffer, and still expires 100ms after receipt.
        assert(queue.enqueue(c, 100, 60, p));
        assert(!queue.enqueue(c, 105, 60, p));
        assert(!queue.apply(p, 159) && p.v == 0);
        assert(queue.apply(p, 160) && p.v == .05f);
        assert(!queue.enqueue(c, 170, 60, p)); // replay cannot renew TTL
        p.tick(199); assert(p.v == .05f);
        p.tick(200); assert(p.v == 0 && !strcmp(p.state(), "disarmed"));
    }
    {
        Protocol p(.1f, .3f); auto c = setup(p, 100);
        CommandScheduler queue;
        assert(queue.enqueue(c, 100, 60, p));
        assert(!queue.apply(p, 181)); // over 20ms late, no delayed surprise motion
        assert(p.v == 0 && p.ackSeq == 2);
        c.seq++;
        assert(queue.enqueue(c, 181, 0, p));
        assert(queue.apply(p, 181)); // exactly due is legitimate
    }
    {
        Protocol p(.1f, .3f); auto c = setup(p, 100);
        CommandScheduler queue;
        assert(queue.enqueue(c, 100, 60, p));
        c.seq = 4; c.v = -.05f;
        assert(queue.enqueue(c, 100, 80, p));
        assert(queue.apply(p, 180));
        assert(p.ackSeq == 4 && p.v == -.05f);
        c.seq = 5; c.v = .05f;
        assert(queue.enqueue(c, 180, 70, p));
        c.seq = 6; c.v = -.05f;
        assert(queue.enqueue(c, 180, 60, p));
        assert(queue.apply(p, 240) && p.ackSeq == 6);
        assert(!queue.apply(p, 250) && p.v == -.05f); // older seq never overwrites newer motion
    }
    {
        Protocol p(.1f, .3f); auto c = setup(p, 100);
        CommandScheduler queue;
        assert(queue.enqueue(c, 100, 60, p));
        c.seq = 4; c.v = 0; c.stop = true;
        assert(p.accept(c, 120)); queue.clear(); // same stop path used by firmware
        assert(!queue.apply(p, 160) && p.v == 0);
        c.seq = 5; c.v = .05f; c.stop = false;
        assert(queue.enqueue(c, 160, 40, p));
        p.linkLost(); queue.clear();
        assert(!queue.apply(p, 200) && p.v == 0);
    }
    {
        Protocol p(.1f, .3f); const uint32_t start = UINT32_MAX-50;
        auto c = setup(p, start); CommandScheduler queue;
        assert(queue.enqueue(c, start, 60, p));
        assert(!queue.apply(p, start+59));
        assert(queue.apply(p, start+60) && p.v == .05f);
        p.tick(start+100); assert(p.v == 0); // deadlines and TTL across millis rollover
    }
    {
        Protocol p(.1f, .3f); auto c = setup(p, 100);
        CommandScheduler queue;
        for (int i = 0; i < 8; ++i) { c.seq = 3+i; assert(queue.enqueue(c, 100, 50+i, p)); }
        c.seq = 11; assert(!queue.enqueue(c, 100, 60, p));
        assert(queue.apply(p, 158) && p.ackSeq == 10);
        assert(queue.enqueue(c, 158, 60, p));
        c.seq = 12; assert(!queue.enqueue(c, 158, 100, p)); // expires before execution
        c.session = "other"; assert(!queue.enqueue(c, 158, 60, p));
    }
    {
        Protocol p(.1f, .3f); auto c = setup(p, 100);
        for (unsigned i = 2; i < 40; ++i) p.sent(i, 100+i);
        CommandScheduler queue;
        assert(queue.enqueue(c, 140, 60, p));
        assert(queue.apply(p, 200)); // urgent telemetry cannot evict an otherwise fresh echo
    }
}
