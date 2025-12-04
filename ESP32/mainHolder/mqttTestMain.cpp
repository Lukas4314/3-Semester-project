#include <Arduino.h>
#include "MqttInterface.hpp"

MqttInterface mqtt("Havefun", "Havefun2", "10.32.162.201");

void setup() {
    Serial.begin(115200);
    mqtt.begin();
}

void loop() {
    mqtt.loop();

    // Example dummy audio buffer
    uint8_t buffer[128];
    for (int i = 0; i < 128; i++) buffer[i] = i;
    if (mqtt.publish("Magne", buffer, sizeof(buffer))) {
        Serial.println("Published successfully");
    } else {
        Serial.println("Publish failed");
    }

    delay(10); // adjust depending on sample chunk timing
}
