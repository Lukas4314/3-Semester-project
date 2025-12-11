#pragma once

#include "driver/i2s_std.h"
#include "driver/gpio.h"
#include "driver/i2s_common.h"
#include "driver/i2s_types.h"

/**
 * @brief Simple OOP wrapper for ESP32 I2S interface (ESP-IDF version)
 */
class I2sInterface {
public:
    
    I2sInterface() = default;


    I2sInterface(
        i2s_port_t port,
        i2s_role_t role,
        i2s_data_bit_width_t dataBitWidth,
        i2s_slot_mode_t slotMode,
        gpio_num_t mclkPin,
        gpio_num_t bclkPin,
        gpio_num_t ws,
        gpio_num_t dataInPin,
        i2s_std_slot_mask_t slotMask,
        uint32_t sampleRate = 44100,
        uint8_t id = 0
    );


    volatile bool overflow_flag;


    bool begin();

    size_t readSamples(void* data, size_t maxBytes);

    uint8_t get_id() const { return id; }
    uint8_t counterOffset = 0;


private:
    i2s_event_callbacks_t cbs;
    i2s_port_t port;
    i2s_role_t role;
    i2s_data_bit_width_t dataBitWidth;
    i2s_slot_mode_t slotMode;
    gpio_num_t mclkPin;
    gpio_num_t bclkPin;
    gpio_num_t ws;
    gpio_num_t dataInPin;
    i2s_std_slot_mask_t slotMask;
    i2s_chan_handle_t rx_chan;
    uint32_t sampleRate;
    uint8_t id;

};
