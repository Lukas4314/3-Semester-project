#include "MqttInterface.hpp"

// Constructor
MqttInterface::MqttInterface(const char* ssid, const char* password, const char* broker, uint16_t port)
    : _ssid(ssid), _password(password), _broker(broker), _port(port), _client(_wifiClient)
{
}

// Initialize Wi-Fi and MQTT
void MqttInterface::begin() {
    connectWiFi();
    _client.setServer(_broker, _port);
}

// Must be called regularly in loop()
void MqttInterface::loop() {
    if (!_client.connected()) {
        reconnect();
    }
    _client.loop();
}

// MqttInterface.cpp
bool MqttInterface::publish(const char* topic, const uint8_t* buffer, size_t length) {
    if (!_client.connected()) return false;
    return _client.publish(topic, buffer, length);
}

bool MqttInterface::publish(const char* topic, const int16_t* buffer, size_t length) {
    if (!_client.connected()) return false;
    bool succes = _client.publish(topic, (const uint8_t*)buffer, length); // length in bytes
    if (!succes) {
        Serial.println("Publish failed inside MqttInterface");
        
    } 
    return succes;
}



// Connect to Wi-Fi
void MqttInterface::connectWiFi() {
    Serial.print("Connecting to Wi-Fi: ");
    Serial.println(_ssid);
    WiFi.begin(_ssid, _password);
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }
    Serial.println("\nWi-Fi connected");
}

// Reconnect to MQTT broker if disconnected
void MqttInterface::reconnect() {
    while (!_client.connected()) {
        Serial.print("Connecting to MQTT broker...");
        if (_client.connect("ESP32AudioClient")) {
            Serial.println("connected");
        } else {
            Serial.print("failed, rc=");
            Serial.print(_client.state());
            Serial.println(" retrying in 2s");
            delay(2000);
        }
    }
}
