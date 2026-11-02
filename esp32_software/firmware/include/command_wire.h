#pragma once
#include <ArduinoJson.h>
#include <cstring>
#include "protocol.h"

inline bool decodeCommand(const char* data, size_t length, const char* id, const char* boot,
                          Protocol::Command& command) {
    if (!length || length > 1024) return false;
    StaticJsonDocument<1536> doc;
    if (deserializeJson(doc, data, length)) return false;
    if (!doc["version"].is<int>() || doc["version"].as<int>() != 1 ||
        !doc["type"].is<const char*>() || strcmp(doc["type"], "command") ||
        !doc["robot_id"].is<const char*>() || strcmp(doc["robot_id"], id) ||
        !doc["boot_id"].is<const char*>() || strcmp(doc["boot_id"], boot) ||
        !doc["session"].is<const char*>() || !doc["seq"].is<uint64_t>() ||
        !doc["telemetry_seq"].is<uint64_t>() || !doc["ttl_ms"].is<uint32_t>() ||
        !doc["stop"].is<bool>() || !doc["v"].is<float>() || !doc["omega"].is<float>() ||
        !doc["action"].is<const char*>()) return false;
    const char* action = doc["action"];
    if (!strcmp(action, "stop")) command.action = Protocol::Action::Stop;
    else if (!strcmp(action, "arm")) command.action = Protocol::Action::Arm;
    else if (!strcmp(action, "drive")) command.action = Protocol::Action::Drive;
    else return false;
    command.session = doc["session"].as<const char*>();
    command.seq = doc["seq"].as<uint64_t>();
    command.telemetry = doc["telemetry_seq"].as<uint64_t>();
    command.v = doc["v"].as<float>(); command.omega = doc["omega"].as<float>();
    command.ttl = doc["ttl_ms"].as<uint32_t>(); command.stop = doc["stop"].as<bool>();
    return true;
}
