#include "I2sInterface.hpp"
#include <stdint.h>
#include "esp_err.h"
#include "esp_log.h"
#include "esp_check.h"
extern "C"
{
#include "esp_rom_sys.h"
}

I2sInterface::I2sInterface(
    i2s_port_t port,
    i2s_role_t role,
    i2s_data_bit_width_t dataBitWidth,
    i2s_slot_mode_t slotMode,
    gpio_num_t mclkPin,
    gpio_num_t bclkPin,
    gpio_num_t ws,
    gpio_num_t dataInPin,
    i2s_std_slot_mask_t slotMask,
    uint32_t sampleRate,
    uint8_t id) : port(port),
                  role(role),
                  dataBitWidth(dataBitWidth),
                  slotMode(slotMode),
                  mclkPin(mclkPin),
                  bclkPin(bclkPin),
                  ws(ws),
                  dataInPin(dataInPin),
                  slotMask(slotMask),
                  sampleRate(sampleRate),
                  id(id)
{
}

IRAM_ATTR static bool i2s_rx_queue_overflow_callback(i2s_chan_handle_t handle,
                                                     i2s_event_data_t *event,
                                                     void *user_ctx)
{
    I2sInterface *iface = (I2sInterface *)user_ctx;
    iface->counterOffset++;
    return false;
}

bool I2sInterface::begin()
{
    //i2s_std_slot_config_t slotConfig = I2S_STD_MSB_SLOT_DEFAULT_CONFIG(dataBitWidth, slotMode);
    i2s_std_slot_config_t slotConfig = I2S_STD_PHILIPS_SLOT_DEFAULT_CONFIG(dataBitWidth, slotMode);
    slotConfig.data_bit_width = dataBitWidth;
    slotConfig.slot_bit_width = I2S_SLOT_BIT_WIDTH_16BIT;
    slotConfig.slot_mode = slotMode;
    slotConfig.slot_mask = slotMask;
    slotConfig.ws_width = 16;
    slotConfig.ws_pol = false;
    slotConfig.bit_shift = true;

    

    i2s_std_config_t stdConfig = {
        .clk_cfg = I2S_STD_CLK_DEFAULT_CONFIG(sampleRate),
        .slot_cfg = slotConfig,
        .gpio_cfg = {
            .mclk = mclkPin,
            .bclk = bclkPin,
            .ws = ws,
            .dout = I2S_GPIO_UNUSED,
            .din = dataInPin,
            .invert_flags = {
                .mclk_inv = false,
                .bclk_inv = false,
                .ws_inv = false,
            },
        },
    };

    i2s_chan_config_t chanConfig = I2S_CHANNEL_DEFAULT_CONFIG(port, role);
    chanConfig.dma_frame_num = 960;
    chanConfig.dma_desc_num = 8;

    esp_err_t err = i2s_new_channel(&chanConfig, NULL, &rx_chan);
    if (err != ESP_OK)
    {
        return false;
    }

    // Register event callbacks
    cbs.on_recv = NULL;
    cbs.on_recv_q_ovf = i2s_rx_queue_overflow_callback;
    cbs.on_sent = NULL;
    cbs.on_send_q_ovf = NULL;

    ESP_ERROR_CHECK(i2s_channel_register_event_callback(rx_chan, &cbs, this));

    err = i2s_channel_init_std_mode(rx_chan, &stdConfig);
    if (err != ESP_OK)
    {
        return false;
    }

    i2s_channel_enable(rx_chan);

    return true;
}

size_t I2sInterface::readSamples(void *data, size_t maxBytes)
{
    size_t bytesRead = 0;
    esp_err_t err = i2s_channel_read(rx_chan, data, maxBytes, &bytesRead, 1000);
    if (err != ESP_OK)
    {
        return 0;
    }
    return bytesRead;
}
