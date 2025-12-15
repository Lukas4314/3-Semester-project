#include "I2sInterface.hpp"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "driver/spi_slave.h"
#include "esp_log.h"

// === Pin definitions ===
#define I2S0_BCLK GPIO_NUM_26
#define I2S0_LRCLK GPIO_NUM_25
#define I2S0_DIN GPIO_NUM_22
// #define I2S0_DIN GPIO_NUM_17

#define I2S1_BCLK GPIO_NUM_16
#define I2S1_LRCLK GPIO_NUM_4
#define I2S1_DIN GPIO_NUM_32

#define MIC1_SEL_PIN GPIO_NUM_13
#define MIC1_SEL_VALUE 0
#define MIC2_SEL_PIN GPIO_NUM_14
#define MIC2_SEL_VALUE 1
#define MIC3_SEL_PIN GPIO_NUM_27
#define MIC3_SEL_VALUE 0


#define SAMPLE_RATE 22050
#define NUM_I2S_BUFFERS 10
#define BUFFER_SIZE 1024

#define BUFFER_SIZE_TOTAL (BUFFER_SIZE * 3 + 4)

static int16_t mic_data[NUM_I2S_BUFFERS][BUFFER_SIZE_TOTAL]; // 3 Mics

// SPI slave buffer for DMA transactions

#define SPI_MAX_CHUNK 4096

static DRAM_ATTR I2sInterface i2s0;
static DRAM_ATTR I2sInterface i2s1;

bool ready = false;

struct I2SBuffer
{
    uint8_t index;
    size_t length; // bytes
};


// Setup function
void setup()
{

    // Mic select pins
    gpio_set_direction(MIC1_SEL_PIN, GPIO_MODE_OUTPUT);
    gpio_set_direction(MIC2_SEL_PIN, GPIO_MODE_OUTPUT);
    gpio_set_direction(MIC3_SEL_PIN, GPIO_MODE_OUTPUT);
    gpio_set_level(MIC1_SEL_PIN, MIC1_SEL_VALUE);
    gpio_set_level(MIC2_SEL_PIN, MIC2_SEL_VALUE);
    gpio_set_level(MIC3_SEL_PIN, MIC3_SEL_VALUE);

    // I2S interfaces
    i2s0 = I2sInterface(I2S_NUM_0, I2S_ROLE_MASTER, I2S_DATA_BIT_WIDTH_16BIT,
                        I2S_SLOT_MODE_STEREO, GPIO_NUM_NC, I2S0_BCLK, I2S0_LRCLK, I2S0_DIN,
                        I2S_STD_SLOT_BOTH, SAMPLE_RATE, 0);
    i2s1 = I2sInterface(I2S_NUM_1, I2S_ROLE_MASTER, I2S_DATA_BIT_WIDTH_16BIT,
                        I2S_SLOT_MODE_STEREO, GPIO_NUM_NC, I2S1_BCLK, I2S1_LRCLK, I2S1_DIN,
                        I2S_STD_SLOT_BOTH, SAMPLE_RATE, 1);
    
    printf("Setup complete\n");

    if (!i2s1.begin())
    {
        printf("I2S1 init failed\n");
        while (1)
            ;
    }

    if (!i2s0.begin())
    {
        printf("I2S init failed\n");
        while (1)
            ;
    }
}

extern "C" void app_main(void)
{
    setup();
    printf("Setup complete, starting tasks...\n");

    uint32_t counter0 = 0;
    uint32_t counter1 = 0;
    uint8_t i2s0Idx = 0;

    const size_t stereoSize = BUFFER_SIZE * 2;
    const size_t monoSize = BUFFER_SIZE;

    static int16_t temp0[stereoSize];
    static int16_t temp1[stereoSize];

    while (true)
    {
        size_t bytesRead0 = i2s0.readSamples(temp0, stereoSize * sizeof(int16_t));
        size_t bytesRead1 = i2s1.readSamples(temp1, stereoSize * sizeof(int16_t));

        printf("%d %d %d    |||     %d %d %d    |||    %d %d %d\n",
               temp0[0], temp0[2], temp0[4], temp0[1], temp0[3], temp0[5],
               temp1[0], temp1[2], temp1[4]);

        if (bytesRead0 != stereoSize * sizeof(int16_t))
        {
            printf("I2S0 read size mismatch: %d bytes\n", bytesRead0);
        }
        if (bytesRead1 != stereoSize * sizeof(int16_t))
        {
            printf("I2S1 read size mismatch: %d bytes\n", bytesRead1);
        }

        uint8_t buf0 = i2s0Idx;
        i2s0Idx = (i2s0Idx + 1) % NUM_I2S_BUFFERS;

        if (i2s0.counterOffset > 0)
        {
            counter0 += i2s0.counterOffset;
            printf("I2S0 counter offset applied: %d\n", i2s0.counterOffset);
            i2s0.counterOffset = 0;
        }
        if (i2s1.counterOffset > 0)
        {
            counter1 += i2s1.counterOffset;
            printf("I2S1 counter offset applied: %d\n", i2s1.counterOffset);
            i2s1.counterOffset = 0;
        }

        // Store counters
        mic_data[buf0][0] = (int16_t)(counter0 & 0xFFFF);
        mic_data[buf0][1] = (int16_t)(counter0 >> 16);
        mic_data[buf0][BUFFER_SIZE * 2 + 2] = (int16_t)(counter1 & 0xFFFF);
        mic_data[buf0][BUFFER_SIZE * 2 + 3] = (int16_t)(counter1 >> 16);

        int16_t mic3_data[monoSize];
        for (size_t i = 0; i < monoSize; i++)
        {
            mic3_data[i] = temp1[i * 2];
        } 
        memcpy(mic_data[buf0] + 2, temp0, bytesRead0);
        memcpy(mic_data[buf0] + BUFFER_SIZE * 2 + 4, mic3_data, monoSize * sizeof(int16_t));

        // Queue buffers for SPI task
        //I2SBuffer msg0 = {buf0, (bytesRead0 + 4 + bytesRead1 + 4)}; // 2 counters * 2 bytes

        counter0++;
        counter1++;
    }
}
