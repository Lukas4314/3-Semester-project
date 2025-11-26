#pragma once
#include <Arduino.h>
#include <driver/i2s.h>

/**
 * @brief Simple OOP wrapper for ESP32 I2S interface
 */
class I2sInterface {
public:
    /**
     * @brief Construct a new I2S interface object
     * 
     * @param port I2S peripheral to use (I2S_NUM_0 or I2S_NUM_1)
     * @param bclkPin GPIO number for Bit Clock (BCLK / SCK)
     * @param lrclkPin GPIO number for Left-Right Clock, meaning left or right channel (LRCLK / WS)
     * @param dataOutPin GPIO number for I2S Data Output (DOUT / TX)
     * @param dataInPin GPIO number for I2S Data Input (DIN / RX). Use -1 if TX only
     * @param mode I2S mode: combination of master/slave, TX/RX
     *        - I2S_MODE_MASTER: ESP32 generates clocks
     *        - I2S_MODE_SLAVE: ESP32 listens to external master
     *        - I2S_MODE_TX: Enable transmission
     *        - I2S_MODE_RX: Enable reception
     *        Default: I2S_MODE_MASTER | I2S_MODE_TX
     * @param bitsPerSample Audio bit depth: 8, 16, 24, or 32 bits per sample
     *        Default: I2S_BITS_PER_SAMPLE_16BIT
     * @param channelFormat Channel format (stereo/mono):
     *        - I2S_CHANNEL_FMT_RIGHT_LEFT: standard stereo
     *        - I2S_CHANNEL_FMT_ONLY_LEFT: left only
     *        - I2S_CHANNEL_FMT_ONLY_RIGHT: right only
     *        Default: I2S_CHANNEL_FMT_RIGHT_LEFT
     * @param sampleRate Audio sample rate in Hz (e.g., 44100, 48000)
     *        Default: 44100
     */
    I2sInterface(
        i2s_port_t port,
        int bclkPin,
        int lrclkPin,
        int dataOutPin,
        int dataInPin,
        i2s_mode_t mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX),
        i2s_bits_per_sample_t bitsPerSample = I2S_BITS_PER_SAMPLE_16BIT,
        i2s_channel_fmt_t channelFormat = I2S_CHANNEL_FMT_RIGHT_LEFT,
        uint32_t sampleRate = 44100
    );

    /**
     * @brief Initialize the I2S peripheral with the configured pins and settings
     * @return true if initialization succeeded, false otherwise
     */
    bool begin();

    /**
     * @brief Stop and uninstall the I2S driver
     */
    void stop();

    /**
     * @brief Write audio samples to the I2S device
     * @param data Pointer to the sample buffer
     * @param bytes Number of bytes to write
     * @return Number of bytes actually written
     */
    size_t writeSamples(const void* data, size_t bytes);

    /**
     * @brief Read audio samples from the I2S device
     * @param data Pointer to buffer to receive samples
     * @param maxBytes Maximum number of bytes to read
     * @return Number of bytes actually read
     */
    size_t readSamples(void* data, size_t maxBytes);

private:
    i2s_port_t _port;
    int _bclkPin;
    int _lrclkPin;
    int _dataOutPin;
    int _dataInPin;
    i2s_mode_t _mode;
    i2s_bits_per_sample_t _bitsPerSample;
    i2s_channel_fmt_t _channelFormat;
    uint32_t _sampleRate;
};
