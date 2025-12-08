#pragma once
#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>

class MqttInterface {
public:
    // Constructor
    MqttInterface(const char* ssid, const char* password, const char* broker, uint16_t port = 1883);

    // Connect to Wi-Fi and MQTT broker
    void begin();

    // Call this regularly in loop()
    void loop();

    // Publish raw buffer to a topic
    bool publish(const char* topic, const uint8_t* buffer, size_t length);
    bool publish(const char* topic, const int16_t* buffer, size_t length); // length in bytes

    void overrideMaxBufferSize(size_t newSize) {
        _client.setBufferSize(newSize);
    }



private:
    const char* _ssid;
    const char* _password;
    const char* _broker;
    uint16_t _port;

    WiFiClient _wifiClient;
    PubSubClient _client;

    void connectWiFi();
    void reconnect();
};
