#include "MqttInterface.hpp"
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <stdlib.h>
#include <inttypes.h>
#include "esp_system.h"
#include "nvs_flash.h"
#include "esp_event.h"
#include "esp_netif.h"
// #include "protocol_examples_common.h"

#include "esp_log.h"
#include "mqtt_client.h"

#include "esp_wifi.h"
#include "nvs_flash.h"

MqttInterface::MqttInterface(const char *ssid, const char *password, const char *broker, uint16_t port)
    : _ssid(ssid), _password(password), _broker(broker), _port(port) {}

void MqttInterface::begin()
{

    connectWiFi();

    printf("Connecting to MQTT broker at %s:%" PRIu16 "\n", _broker, _port);
    esp_mqtt_client_config_t mqtt_cfg = {};
    mqtt_cfg.broker.address.uri = _broker;

    _client = esp_mqtt_client_init(&mqtt_cfg);
    /* The last argument may be used to pass data to the event handler, in this example mqtt_event_handler */
    esp_mqtt_client_start(_client);
}

bool MqttInterface::publish(const char *topic, const int16_t *buffer, size_t length)
{
    int msg_id = esp_mqtt_client_publish(_client, topic, (const char *)buffer, length, 0, 0);
    if (msg_id == -1 || msg_id == -2)
    {
        if (msg_id == -1)
        {
            printf("MQTT publish failed: Out of memory\n");
        }
        else if (msg_id == -2)
        {
            printf("MQTT publish failed: Full outbox\n");
        }
        printf("Failed to publish to topic %s\n", topic);
        return false;
    }
    return true;
}

void MqttInterface::wifi_event_handler(void *arg,
                                       esp_event_base_t event_base,
                                       int32_t event_id,
                                       void *event_data)
{
    MqttInterface *self = static_cast<MqttInterface *>(arg);

    if (event_base == IP_EVENT && event_id == IP_EVENT_STA_GOT_IP)
    {
        printf("EVENT HANDLER: GOT IP -> setting bit\n");
        xEventGroupSetBits(self->wifi_event_group, WIFI_CONNECTED_BIT);
    }
}

void MqttInterface::connectWiFi()
{
    printf("Connecting to WiFi SSID: %s\n", _ssid);

    // --- NVS ---
    esp_err_t ret = nvs_flash_init();
    printf("NVS flash init returned: %d\n", ret);
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND)
    {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ESP_ERROR_CHECK(nvs_flash_init());
    }
    printf("NVS initialized.\n");

    // --- Netif + Event Loop ---
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    esp_netif_create_default_wifi_sta();

    printf("WiFi driver initializing...\n");

    // Create EventGroup BEFORE events happen
    wifi_event_group = xEventGroupCreate();

    // --- WiFi Driver ---
    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));

    printf("WiFi driver initialized.\n");
    // Event handlers
    ESP_ERROR_CHECK(esp_event_handler_instance_register(
        IP_EVENT,
        IP_EVENT_STA_GOT_IP,
        &MqttInterface::wifi_event_handler,
        this,
        nullptr));

    // --- WiFi Config ---
    wifi_config_t wifi_config = {};
    strncpy((char *)wifi_config.sta.ssid, _ssid, sizeof(wifi_config.sta.ssid));
    strncpy((char *)wifi_config.sta.password, _password, sizeof(wifi_config.sta.password));

    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &wifi_config));

    printf("Starting WiFi...\n");
    ESP_ERROR_CHECK(esp_wifi_start());
    printf("WiFi started, now connecting...\n");
    ESP_ERROR_CHECK(esp_wifi_connect());

    printf("Waiting for IP event...\n");

    xEventGroupWaitBits(
        wifi_event_group,
        WIFI_CONNECTED_BIT,
        pdFALSE,
        pdFALSE,
        portMAX_DELAY);

    printf("WiFi READY.\n");
}