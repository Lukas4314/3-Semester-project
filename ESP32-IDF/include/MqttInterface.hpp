#pragma once
#include <driver/gpio.h>
#include <mqtt_client.h>

class MqttInterface {
public:
    // Constructor
    MqttInterface() = default;
    MqttInterface(const char* ssid, const char* password, const char* broker, uint16_t port = 1883);

    // Connect to Wi-Fi and MQTT broker
    void begin();

    // Call this regularly in loop()
    void loop();

    // Publish raw buffer to a topic
    bool publish(const char* topic, const int16_t* buffer, size_t length); // length in bytes
    bool enqueue(const char* topic, const int16_t* buffer, size_t length); // length in bytes


private:
    const char* _ssid;
    const char* _password;
    const char* _broker;
    uint16_t _port;
    esp_mqtt_client_handle_t _client;




    EventGroupHandle_t wifi_event_group;
    static const int WIFI_CONNECTED_BIT = BIT0;

    void connectWiFi();
    void reconnect();   

    static void wifi_event_handler(void* arg, esp_event_base_t event_base,
                                   int32_t event_id, void* event_data);
};

