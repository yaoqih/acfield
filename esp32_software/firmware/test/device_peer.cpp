// Host peer using the actual JSON decoder and device acceptance state machine.
#include <ArduinoJson.h>
#include <iostream>
#include <string>
#include "command_wire.h"
int main() {
    Protocol p(.1f, .3f);
    std::string line;
    while (std::getline(std::cin, line)) {
        StaticJsonDocument<2048> input;
        if (deserializeJson(input, line)) return 2;
        uint32_t now = input["now"] | 100;
        const char* op = input["op"] | "command";
        bool accepted = false;
        if (!strcmp(op, "sent")) p.sent(input["seq"].as<uint64_t>(), now);
        else if (!strcmp(op, "tick")) p.tick(now);
        else if (!strcmp(op, "link_lost")) p.linkLost();
        else {
            std::string packet;
            serializeJson(input["packet"], packet);
            Protocol::Command c;
            accepted = decodeCommand(packet.c_str(), packet.size(), "car-01", "test-boot", c) && p.accept(c, now);
        }
        StaticJsonDocument<1024> out;
        out["accepted"] = accepted; out["device_state"] = p.state();
        out["v"] = p.v; out["omega"] = p.omega; out["stop_reason"] = p.reason;
        if (p.hasAck) { out["ack_session"] = p.session; out["ack_seq"] = p.ackSeq; }
        std::string json; serializeJson(out, json); std::cout << json << std::endl;
    }
}
