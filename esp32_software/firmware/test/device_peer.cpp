// Host peer using the actual JSON decoder and device acceptance state machine.
#include <ArduinoJson.h>
#include <iostream>
#include <string>
#include "command_wire.h"
#include "voltage_guard.h"
int main() {
    Protocol p(.1f, .3f);
    VoltageGuard battery;
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
        else if (!strcmp(op, "battery")) {
            const float voltage = input["voltage_v"].isNull() ? NAN : input["voltage_v"].as<float>();
            if (const char* fault = battery.check(voltage, now)) p.fault(fault);
        }
        else {
            std::string packet;
            serializeJson(input["packet"], packet);
            // Match receive(): ArduinoJson parses the mutable UDP buffer in place.
            StaticJsonDocument<1536> envelope;
            const auto error = deserializeJson(envelope, &packet[0], packet.size());
            Protocol::Command c;
            accepted = !error && packet.size() <= 1024 &&
                decodeCommand(envelope.as<JsonVariantConst>(), "car-01", "test-boot", c) && p.accept(c, now);
        }
        StaticJsonDocument<1024> out;
        out["accepted"] = accepted; out["device_state"] = p.state();
        out["v"] = p.v; out["omega"] = p.omega; out["stop_reason"] = p.reason;
        out["fault"] = p.faultCode(); out["warning"] = battery.warningCode();
        if (p.hasAck) { out["ack_session"] = p.session; out["ack_seq"] = p.ackSeq; }
        std::string json; serializeJson(out, json); std::cout << json << std::endl;
    }
}
