#include <Arduino.h>
#include <ArduinoJson.h>
#include <WiFi.h>
#include <WiFiUdp.h>
#include <esp_task_wdt.h>
#include "battery.h"
#include "motors.h"
#include "command_wire.h"
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
Protocol protocol(config::maxV, config::maxOmega);
SemaphoreHandle_t stateMutex;
char bootId[33];
uint64_t telemetrySeq = 0;
uint32_t lastTelemetry = 0, lastBattery = 0;
bool connected = false;

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
        if (protocol.v == 0 && protocol.omega == 0) motors.stop();
        motors.update(protocol.v, protocol.omega, dt);
        if (motors.fault) { protocol.fault(motors.fault); motors.stop(); }
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
    Protocol::Command command;
    if (n != size || !decodeCommand(buffer, n, config::robotId, bootId, command)) return;
    xSemaphoreTake(stateMutex, portMAX_DELAY);
    if (protocol.accept(command, millis()) && protocol.v == 0 && protocol.omega == 0) motors.stop();
    xSemaphoreGive(stateMutex);
}

void telemetry() {
    StaticJsonDocument<2048> doc;
    doc["version"] = 1; doc["type"] = "telemetry";
    doc["robot_id"] = config::robotId; doc["boot_id"] = bootId;
    doc["seq"] = telemetrySeq; doc["firmware"] = config::firmware;
    doc["battery"] = nullptr;
    if (battery.valid) doc["voltage_v"] = battery.voltage;
    else doc["voltage_v"] = nullptr;
    doc["limits"]["max_v"] = config::maxV; doc["limits"]["max_omega"] = config::maxOmega;
    xSemaphoreTake(stateMutex, portMAX_DELAY);
    if (config::calibrated()) {
        doc["measured_v"] = motors.measuredV; doc["measured_omega"] = motors.measuredOmega;
        doc["wheel_left"] = motors.speed[0]; doc["wheel_right"] = motors.speed[1];
    }
    doc["encoder_left"] = motors.encoder[0]; doc["encoder_right"] = motors.encoder[1];
    doc["device_state"] = protocol.state(); doc["stop_reason"] = protocol.reason;
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
    WiFi.setAutoReconnect(true); WiFi.begin(wifiSsid, wifiPassword);
    Serial.printf("Robot %s, firmware %s, boot %s\n", config::robotId, config::firmware, bootId);
}

void loop() {
    ESP_ERROR_CHECK(esp_task_wdt_reset());
    const uint32_t now = millis();
    bool online = WiFi.status() == WL_CONNECTED;
    if (online != connected) {
        xSemaphoreTake(stateMutex, portMAX_DELAY);
        protocol.linkLost(); motors.stop();
        xSemaphoreGive(stateMutex);
        udp.stop();
        if (online && !udp.begin(config::localPort)) online = false;
        connected = online;
    }
    if (uint32_t(now-lastBattery) >= config::batteryMs) {
        lastBattery = now;
        if (const char* fault = battery.sample(now)) {
            xSemaphoreTake(stateMutex, portMAX_DELAY);
            protocol.fault(fault); motors.stop();
            xSemaphoreGive(stateMutex);
        }
    }
    if (online) receive();
    if (online && uint32_t(now-lastTelemetry) >= config::telemetryMs) {
        lastTelemetry = now; telemetry();
    }
    delay(1);
}
