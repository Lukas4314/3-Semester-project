#include "I2sInterface.hpp"
#include "MqttInterface.hpp"
#include "esp_timer.h"
#include "esp_memory_utils.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"

// === Pin definitions ===
#define I2S0_BCLK GPIO_NUM_26
#define I2S0_LRCLK GPIO_NUM_25
#define I2S0_DIN GPIO_NUM_22

#define I2S1_BCLK GPIO_NUM_16
#define I2S1_LRCLK GPIO_NUM_4
#define I2S1_DIN GPIO_NUM_32

#define MIC1_SEL_PIN GPIO_NUM_13
#define MIC1_SEL_VALUE 0
#define MIC2_SEL_PIN GPIO_NUM_14
#define MIC2_SEL_VALUE 1
#define MIC3_SEL_PIN GPIO_NUM_27
#define MIC3_SEL_VALUE 0

#define SAMPLE_RATE 16000

#define BUFFER_SIZE 1024
static int16_t i2s0Buffer[BUFFER_SIZE * 2 + 2]; // stereo + 2 counters
static int16_t i2s1Buffer[BUFFER_SIZE + 2];     // mono + 2 counters



MqttInterface mqtt("Havefun", "Havefun2", "mqtt://10.250.34.201"); // MQTT instance

static DRAM_ATTR I2sInterface i2s0;
static DRAM_ATTR I2sInterface i2s1;

// Queue to send buffers from CPU1 (I2S task) to CPU0 (MQTT task)
struct I2SBuffer
{
    int16_t *data;
    size_t length;
};
QueueHandle_t i2sQueue;

// Setup function: called once on CPU0
void setup()
{
    mqtt.begin();
    printf("Initialized MQTT interface...\n");

    // Set mic select pins
    gpio_set_direction(MIC1_SEL_PIN, GPIO_MODE_OUTPUT);
    gpio_set_direction(MIC2_SEL_PIN, GPIO_MODE_OUTPUT);
    gpio_set_direction(MIC3_SEL_PIN, GPIO_MODE_OUTPUT);
    gpio_set_level(MIC1_SEL_PIN, MIC1_SEL_VALUE);
    gpio_set_level(MIC2_SEL_PIN, MIC2_SEL_VALUE);
    gpio_set_level(MIC3_SEL_PIN, MIC3_SEL_VALUE);

    // Initialize I2S interfaces
    i2s0 = I2sInterface(
        I2S_NUM_0, I2S_ROLE_MASTER, I2S_DATA_BIT_WIDTH_16BIT,
        I2S_SLOT_MODE_STEREO, GPIO_NUM_NC, I2S0_BCLK, I2S0_LRCLK, I2S0_DIN,
        I2S_STD_SLOT_BOTH, SAMPLE_RATE, 0);

    i2s1 = I2sInterface(
        I2S_NUM_1, I2S_ROLE_SLAVE, I2S_DATA_BIT_WIDTH_16BIT,
        I2S_SLOT_MODE_MONO, GPIO_NUM_NC, I2S1_BCLK, I2S1_LRCLK, I2S1_DIN,
        I2S_STD_SLOT_LEFT, SAMPLE_RATE, 1);

    printf("Initializing I2S interfaces...\n");
    if (!i2s1.begin())
    {
        printf("Failed to initialize I2S1\n");
        while (1)
            ;
    }
    if (!i2s0.begin())
    {
        printf("Failed to initialize I2S0\n");
        while (1)
            ;
    }

    // Create queue for passing I2S buffers to MQTT task
    i2sQueue = xQueueCreate(128, sizeof(I2SBuffer));
}

// CPU1 task: reads I2S and prepares buffers

void i2sTask(void *param)
{
    uint32_t counter0 = 0;
    uint32_t counter1 = 0;

    const size_t bufferSize0 = BUFFER_SIZE * 2; // stereo
    const size_t bufferSize1 = BUFFER_SIZE;     // mono

    int16_t temp0[bufferSize0];
    int16_t temp1[bufferSize1];

    while (true)
    {
        // Read samples from I2S peripherals
        size_t bytesRead0 = i2s0.readSamples(temp0, bufferSize0 * sizeof(int16_t));
        size_t bytesRead1 = i2s1.readSamples(temp1, bufferSize1 * sizeof(int16_t));

        // Handle I2S counter offsets
        if (i2s0.counterOffset != 0)
        {
            counter0 += i2s0.counterOffset;
            printf("I2S0 overflow, total offset: %u\n", i2s0.counterOffset);
            i2s0.counterOffset = 0;
        }
        if (i2s1.counterOffset != 0)
        {
            counter1 += i2s1.counterOffset;
            printf("I2S1 overflow, total offset: %u\n", i2s1.counterOffset);
            i2s1.counterOffset = 0;
        }

        // Convert bytes to sample count
        size_t numSamples0 = bytesRead0 / sizeof(int16_t);
        size_t numSamples1 = bytesRead1 / sizeof(int16_t);


        if (numSamples0 != BUFFER_SIZE*2 || numSamples1 != BUFFER_SIZE)
        {
            // Incomplete buffer read; skip this iteration
            printf("Incomplete I2S read: I2S0 samples=%zu, I2S1 samples=%zu\n", numSamples0, numSamples1);
        }


        // Insert counters at the start of the pre-allocated buffers
        i2s0Buffer[0] = (int16_t)(counter0 & 0xFFFF);
        i2s0Buffer[1] = (int16_t)((counter0 >> 16) & 0xFFFF);
        i2s1Buffer[0] = (int16_t)(counter1 & 0xFFFF);
        i2s1Buffer[1] = (int16_t)((counter1 >> 16) & 0xFFFF);

        // Copy I2S data after counters
        memcpy(i2s0Buffer + 2, temp0, bytesRead0);
        memcpy(i2s1Buffer + 2, temp1, bytesRead1);

        // Send to MQTT task via queue (non-blocking)
        I2SBuffer msg0 = {i2s0Buffer, (numSamples0 + 2) * sizeof(int16_t)};
        I2SBuffer msg1 = {i2s1Buffer, (numSamples1 + 2) * sizeof(int16_t)};

        if (xQueueSend(i2sQueue, &msg0, 0) != pdTRUE)
        {
            // Queue full → drop buffer
            printf("Dropped I2S0 buffer\n");
        }
        if (xQueueSend(i2sQueue, &msg1, 0) != pdTRUE)
        {
            printf("Dropped I2S1 buffer\n");
        }
    }
}

void mqttTask(void *param)
{
    const size_t batchBufferSize = (1024 + 2) * 3 * 3; // space for 9 buffers of 1024 samples + 2 counters
    int16_t batchBuffer[batchBufferSize];
    size_t batchOffset = 0;

    while (true)
    {
        I2SBuffer msg;
        if (xQueueReceive(i2sQueue, &msg, portMAX_DELAY) == pdTRUE)
        {
            // Make sure we don't overflow batch buffer
            if (batchOffset + msg.length / sizeof(int16_t) > batchBufferSize)
            {
                if (batchOffset > 0)
                {
                    mqtt.publish("I2SBatch", batchBuffer, batchOffset * sizeof(int16_t));
                    batchOffset = 0;
                }
            }

            // Copy buffer into batch
            memcpy(batchBuffer + batchOffset, msg.data, msg.length);
            batchOffset += msg.length / sizeof(int16_t);

        }
    }
}

extern "C" void app_main(void)
{
    setup();
    printf("Setup complete, starting tasks...\n");

    // Create I2S task on CPU1
    xTaskCreatePinnedToCore(i2sTask, "I2S_Task", 8192*2, nullptr, 5, nullptr, 1);

    // Create MQTT task on CPU0
    xTaskCreatePinnedToCore(mqttTask, "MQTT_Task", 4096*6, nullptr, 5, nullptr, 0);
}
