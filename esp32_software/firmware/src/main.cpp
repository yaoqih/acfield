#include <Arduino.h>
#include <ArduinoJson.h>
#include <WiFi.h>
#include <WiFiUdp.h>
#include <esp_task_wdt.h>
#include <esp_timer.h>
#include "time_sync.h"
#include "battery.h"
#include "motors.h"
#include "command_wire.h"
#include "command_scheduler.h"
#if __has_include("secrets.h")
#include "secrets.h"
#else
#include "secrets.example.h"
#endif

namespace {
WiFiUDP udp;
IPAddress server;
Motors motors;
Battery battery;
Protocol protocol(config::maxV, config::maxOmega, config::motionEchoMs);
SemaphoreHandle_t stateMutex;
char bootId[33];
uint64_t telemetrySeq = 0;
uint32_t lastTelemetry = 0;
uint32_t lastDebug = 0;
bool connected = false;
TimeSync clockSync;
uint32_t syncId = 0, lastSync = 0;
double syncT1 = 0;
bool syncPending = false;
CommandScheduler scheduled;
uint64_t appliedSeq = 0;
bool urgentTelemetry = false;
double monoMs() { return esp_timer_get_time()/1000.; }

void requestTime(uint32_t now) {
    if (uint32_t(now-lastSync) < 1000) return;
    lastSync = now;
    syncT1 = floor(monoMs()); ++syncId; syncPending = true;
    StaticJsonDocument<192> doc;
    doc["type"] = "time_sync"; doc["id"] = syncId; doc["t1"] = uint64_t(syncT1);
    char buffer[192]; size_t n = serializeJson(doc, buffer, sizeof(buffer));
    if (udp.beginPacket(server, config::serverPort)) { udp.write((const uint8_t*)buffer, n); udp.endPacket(); }
}

void control(void*) {
    ESP_ERROR_CHECK(esp_task_wdt_add(nullptr));
    TickType_t wake = xTaskGetTickCount();
    uint32_t previous = millis();
    while (true) {
        vTaskDelayUntil(&wake, pdMS_TO_TICKS(config::controlMs));
        ESP_ERROR_CHECK(esp_task_wdt_reset());
        uint32_t now = millis();
        float dt = uint32_t(now-previous)*.001f;
        previous = now;
        xSemaphoreTake(stateMutex, portMAX_DELAY);
        protocol.tick(now);
        if (scheduled.apply(protocol, now)) urgentTelemetry = true;
        if (protocol.v == 0 && protocol.omega == 0) motors.stop();
        motors.update(protocol.v, protocol.omega, dt);
        if (protocol.hasAck) appliedSeq = protocol.ackSeq;
        if (motors.fault) { protocol.fault(motors.fault); motors.stop(); }
        xSemaphoreGive(stateMutex);
    }
}

void sampleBattery(void*) {
    Battery sampler;
    TickType_t wake = xTaskGetTickCount();
    while (true) {
        vTaskDelayUntil(&wake, pdMS_TO_TICKS(config::batteryMs));
        const char* fault = sampler.sample(millis());
        xSemaphoreTake(stateMutex, portMAX_DELAY);
        battery.valid = sampler.valid; battery.voltage = sampler.voltage;
        if (battery.warning != sampler.warning) urgentTelemetry = true;
        battery.warning = sampler.warning;
        if (fault) { protocol.fault(fault); motors.stop(); urgentTelemetry = true; }
        xSemaphoreGive(stateMutex);
    }
}

void receive() {
    const int size = udp.parsePacket();
    if (!size) return;
    if (udp.remoteIP() != server || udp.remotePort() != config::serverPort || size > 1024) {
        udp.flush(); return;
    }
    char buffer[1024];
    int n = udp.read(buffer, sizeof(buffer));
    if (n != size) return;
    StaticJsonDocument<1536> envelope;
    if (deserializeJson(envelope, buffer, n)) return;
    if (envelope["type"] == "time_sync") {
        const double t4 = monoMs();
        if (syncPending && envelope["id"].is<uint32_t>() && envelope["id"].as<uint32_t>() == syncId &&
            fabs(envelope["t1"].as<double>()-syncT1) < .01 && envelope["t2"].is<double>() && envelope["t3"].is<double>()) {
            syncPending = false;
            clockSync.observe(syncT1, envelope["t2"], envelope["t3"], t4);
        }
        return;
    }
    Protocol::Command command;
    // The envelope owns references into the mutated input buffer; decode it directly.
    if (!decodeCommand(envelope.as<JsonVariantConst>(), config::robotId, bootId, command)) return;
    if (!envelope["execute_at_ms"].isNull() && command.action == Protocol::Action::Drive &&
        (command.v != 0 || command.omega != 0)) {
        if (!envelope["execute_at_ms"].is<double>()) return;
        const double mono = monoMs();
        const double wait = envelope["execute_at_ms"].as<double>()-clockSync.now(mono);
        if (!clockSync.ready(mono) || !std::isfinite(wait) || wait < 0 || wait > 150 || wait >= command.ttl) return;
        xSemaphoreTake(stateMutex, portMAX_DELAY);
        scheduled.enqueue(command, millis(), uint32_t(ceil(wait)), protocol);
        xSemaphoreGive(stateMutex);
        return;
    }
    xSemaphoreTake(stateMutex, portMAX_DELAY);
    // Only an accepted immediate command can invalidate scheduled motion.
    if (protocol.accept(command, millis())) {
        scheduled.clear();
        urgentTelemetry = true;
        if (protocol.v == 0 && protocol.omega == 0) motors.stop();
    }
    xSemaphoreGive(stateMutex);
}

void telemetry() {
    StaticJsonDocument<2048> doc;
    doc["version"] = 1; doc["type"] = "telemetry";
    doc["robot_id"] = config::robotId; doc["boot_id"] = bootId;
    doc["seq"] = telemetrySeq; doc["firmware"] = config::firmware;
    doc["battery"] = nullptr;
    const double mono = monoMs();
    const double utc = clockSync.now(mono); // keep slewing even while uncertainty blocks motion
    doc["clock_synced"] = clockSync.ready(mono);
    if (clockSync.ready(mono)) {
        // ArduinoJson's floating-point serializer keeps only ~10 significant digits.
        // Integer epoch milliseconds preserve millisecond precision at today's dates.
        doc["sampled_at_ms"] = uint64_t(llround(utc));
        doc["clock_uncertainty_ms"] = clockSync.uncertainty(mono);
    }
    xSemaphoreTake(stateMutex, portMAX_DELAY);
    if (battery.valid) doc["voltage_v"] = battery.voltage;
    else doc["voltage_v"] = nullptr;
    doc["warning"] = battery.warning;
    xSemaphoreGive(stateMutex);
    doc["limits"]["max_v"] = config::maxV; doc["limits"]["max_omega"] = config::maxOmega;
    xSemaphoreTake(stateMutex, portMAX_DELAY);
    if (config::calibrated()) {
        doc["measured_v"] = motors.measuredV; doc["measured_omega"] = motors.measuredOmega;
        doc["wheel_left"] = motors.speed[0]; doc["wheel_right"] = motors.speed[1];
    }
    doc["applied_seq"] = appliedSeq;
    urgentTelemetry = false;
    doc["encoder_left"] = motors.encoder[0]; doc["encoder_right"] = motors.encoder[1];
    doc["device_state"] = protocol.state(); doc["stop_reason"] = protocol.reason;
    doc["motion_echo_rejections"] = protocol.motionEchoRejections;
    doc["fault"] = protocol.faultCode();
    if (protocol.hasAck) {
        doc["ack_session"] = protocol.session; doc["ack_seq"] = protocol.ackSeq;
    } else { doc["ack_session"] = nullptr; doc["ack_seq"] = nullptr; }
    xSemaphoreGive(stateMutex);
    char buffer[1536];
    size_t n = serializeJson(doc, buffer, sizeof(buffer));
    if (!doc.overflowed() && n < sizeof(buffer) && udp.beginPacket(server, config::serverPort)) {
        udp.write(reinterpret_cast<const uint8_t*>(buffer), n);
        if (udp.endPacket()) {
            xSemaphoreTake(stateMutex, portMAX_DELAY);
            protocol.sent(telemetrySeq, millis());
            xSemaphoreGive(stateMutex);
        }
    }
    ++telemetrySeq;
}

void debugStatus(uint32_t now) {
    if (uint32_t(now - lastDebug) < 1000) return;
    lastDebug = now;
    const bool wifiConnected = WiFi.status() == WL_CONNECTED;
    const String localIP = wifiConnected ? WiFi.localIP().toString() : "-";
    const int rssi = wifiConnected ? WiFi.RSSI() : 0;
    xSemaphoreTake(stateMutex, portMAX_DELAY);
    char line[512];
    snprintf(line, sizeof(line), "[status] wifi=%s local=%s rssi=%d udp=%s state=%s fault=%s warning=%s cmd=%.3f/%.3f target=%.3f/%.3f speed=%.3f/%.3f pwm=%.1f/%.1f enc=%lld/%lld voltage=%.2fV\n",
                  wifiConnected ? "connected" : "disconnected", localIP.c_str(), rssi,
                  connected ? "ready" : "off",
                  protocol.state(), protocol.faultCode() ? protocol.faultCode() : "none",
                  battery.warning ? battery.warning : "none",
                  protocol.v, protocol.omega,
                  motors.target[0], motors.target[1], motors.speed[0], motors.speed[1],
                  motors.pwm[0], motors.pwm[1],
                  static_cast<long long>(motors.encoder[0]),
                  static_cast<long long>(motors.encoder[1]),
                  battery.valid ? battery.voltage : NAN);
    xSemaphoreGive(stateMutex);
    Serial.print(line);
}
}

void setup() {
    motors.begin();
    Serial.begin(115200);
    stateMutex = xSemaphoreCreateMutex();
    if (!stateMutex) abort();
    if (!config::motorsEnabled) protocol.fault("motors_disabled");
    else if (!config::calibrated()) protocol.fault("encoder_calibration_required");
    battery.begin();
    delay(20); // INA219 conversion startup, with motor outputs held at zero
    if (const char* fault = battery.sample(millis())) protocol.fault(fault);
    WiFi.persistent(false); WiFi.mode(WIFI_STA); WiFi.setSleep(false);
    snprintf(bootId, sizeof(bootId), "%08lx%08lx%08lx%08lx",
             (unsigned long)esp_random(), (unsigned long)esp_random(),
             (unsigned long)esp_random(), (unsigned long)esp_random());
    ESP_ERROR_CHECK(esp_task_wdt_init(1, true));
    ESP_ERROR_CHECK(esp_task_wdt_add(nullptr));
    if (!server.fromString(serverIp)) {
        Serial.println("Invalid serverIp; halted");
        while (true) { motors.stop(); esp_task_wdt_reset(); delay(100); }
    }
    if (xTaskCreatePinnedToCore(control, "motor-control", 4096, nullptr, 3, nullptr, 1) != pdPASS) abort();
    if (xTaskCreatePinnedToCore(sampleBattery, "battery", 3072, nullptr, 1, nullptr, 0) != pdPASS) abort();
    WiFi.setAutoReconnect(true); WiFi.begin(wifiSsid, wifiPassword);
    Serial.printf("Robot %s, firmware %s, boot %s\n", config::robotId, config::firmware, bootId);
    Serial.printf("Motor control: %s\n", config::encoderDiagnostic ? "diagnostic_open_loop" :
                  config::motorClosedLoop ? "closed_loop" : "open_loop");
}

void loop() {
    ESP_ERROR_CHECK(esp_task_wdt_reset());
    const uint32_t now = millis();
    bool online = WiFi.status() == WL_CONNECTED;
    if (online != connected) {
        xSemaphoreTake(stateMutex, portMAX_DELAY);
        protocol.linkLost(); motors.stop();
        scheduled.clear();
        clockSync.reset(); syncPending = false;
        xSemaphoreGive(stateMutex);
        udp.stop();
        if (online && !udp.begin(config::localPort)) online = false;
        connected = online;
    }
    if (online) {
        // Bounded draining prevents stale datagrams from accumulating indefinitely.
        for (unsigned i = 0; i < 8; ++i) receive();
        requestTime(now);
    }
    bool urgent;
    xSemaphoreTake(stateMutex, portMAX_DELAY);
    urgent = urgentTelemetry;
    xSemaphoreGive(stateMutex);
    if (online && (urgent || uint32_t(now-lastTelemetry) >= config::telemetryMs)) {
        lastTelemetry = now; telemetry();
    }
    debugStatus(now);
    delay(1);
}
