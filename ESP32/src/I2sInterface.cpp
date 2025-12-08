#include "I2sInterface.hpp"

I2sInterface::I2sInterface(
    i2s_port_t port,
    int bclkPin,
    int lrclkPin,
    int dataOutPin,
    int dataInPin,
    i2s_mode_t mode,
    i2s_bits_per_sample_t bitsPerSample,
    i2s_channel_fmt_t channelFormat,
    uint32_t sampleRate
) : _port(port),
    _bclkPin(bclkPin),
    _lrclkPin(lrclkPin),
    _dataOutPin(dataOutPin),
    _dataInPin(dataInPin),
    _mode(mode),
    _bitsPerSample(bitsPerSample),
    _channelFormat(channelFormat),
    _sampleRate(sampleRate)
{}

bool I2sInterface::begin() {
    i2s_config_t config = {
        .mode = _mode,                                          // I2S operating mode: master/slave, RX/TX, etc.
        .sample_rate = _sampleRate,                             // Sampling frequency in Hz (e.g., 44100)
        .bits_per_sample = _bitsPerSample,                      // Bits per audio sample (e.g., 16-bit)
        .channel_format = _channelFormat,                       // Channel format: mono, stereo, etc.
        .communication_format = I2S_COMM_FORMAT_STAND_I2S,      // Standard I2S format (L/R aligned)
        .intr_alloc_flags = 0,                                  // Interrupt allocation flags (0 = default, level 1)
        .dma_buf_count = 16,                                     // Number of DMA buffers used by I2S
        .dma_buf_len = 1024,                                    // Size of each DMA buffer in "samples per channel"
        .use_apll = false,                                      // Use APLL for higher precision clock (false = use default)
        .tx_desc_auto_clear = true,                             // Automatically clear TX descriptor on underflow
        .fixed_mclk = 0                                         // Fixed master clock frequency; 0 means default
    };


    i2s_pin_config_t pinConfig = {
        .bck_io_num = _bclkPin,
        .ws_io_num = _lrclkPin,
        .data_out_num = _dataOutPin,
        .data_in_num = _dataInPin
    };

    if (i2s_driver_install(_port, &config, 0, NULL) != ESP_OK)
        return false;

    if (i2s_set_pin(_port, &pinConfig) != ESP_OK)
        return false;

    return true;
}

void I2sInterface::stop() {
    i2s_driver_uninstall(_port);
}

size_t I2sInterface::writeSamples(const void *data, size_t bytes) {
    size_t written = 0;
    i2s_write(_port, data, bytes, &written, portMAX_DELAY);
    return written;
}

size_t I2sInterface::readSamples(void *data, size_t maxBytes) {
    size_t read = 0;
    i2s_read(_port, data, maxBytes, &read, portMAX_DELAY);
    return read;
}
