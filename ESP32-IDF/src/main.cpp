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

#define NUM_I2S_BUFFERS 10
#define BUFFER_SIZE 1024

static int16_t i2s0Buffers[NUM_I2S_BUFFERS][BUFFER_SIZE * 2 + 2]; // stereo + 2 counters
static int16_t i2s1Buffers[NUM_I2S_BUFFERS][BUFFER_SIZE + 2];     // mono + 2 counters

MqttInterface mqtt("Havefun", "Havefun2", "mqtt://10.250.34.201"); // MQTT instance

static DRAM_ATTR I2sInterface i2s0;
static DRAM_ATTR I2sInterface i2s1;

// Queue to send buffers from CPU1 (I2S task) to CPU0 (MQTT task)
struct I2SBuffer
{
    uint8_t index; // which buffer number
    uint8_t which; // 0 = I2S0, 1 = I2S1
    size_t length; // length in bytes
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
    i2sQueue = xQueueCreate(NUM_I2S_BUFFERS - 1, sizeof(I2SBuffer)); // minus for to make sure
}

void i2sTask(void *param)
{
    uint32_t counter0 = 0;
    uint32_t counter1 = 0;

    uint8_t i2s0Idx = 0;
    uint8_t i2s1Idx = 0;

    const size_t stereoSize = BUFFER_SIZE * 2;
    const size_t monoSize = BUFFER_SIZE;

    int16_t temp0[stereoSize];
    int16_t temp1[monoSize];

    while (true)
    {
        size_t bytesRead0 = i2s0.readSamples(temp0, stereoSize * sizeof(int16_t));
        size_t bytesRead1 = i2s1.readSamples(temp1, monoSize * sizeof(int16_t));

        size_t samples0 = bytesRead0 / sizeof(int16_t);
        size_t samples1 = bytesRead1 / sizeof(int16_t);

        if (samples0 != stereoSize || samples1 != monoSize)
        {
            printf("I2S readSamples returned unexpected number of samples: I2S0=%u, I2S1=%u\n", (unsigned)samples0, (unsigned)samples1);
        }

        // pick buffer index (safe because queue size == NUM_I2S_BUFFERS)
        uint8_t buf0 = i2s0Idx;
        uint8_t buf1 = i2s1Idx;

        i2s0Idx = (i2s0Idx + 1) % NUM_I2S_BUFFERS;
        i2s1Idx = (i2s1Idx + 1) % NUM_I2S_BUFFERS;

        if (i2s0.counterOffset > 0)
        {
            counter0 += i2s0.counterOffset * stereoSize;
            printf("I2S0 overflow, offset=%u\n", i2s0.counterOffset);
            i2s0.counterOffset = 0;
        }
        if (i2s1.counterOffset > 0)
        {
            counter1 += i2s1.counterOffset * monoSize;
            printf("I2S1 overflow, offset=%u\n", i2s1.counterOffset);
            i2s1.counterOffset = 0;
        }

        // Write counters
        i2s0Buffers[buf0][0] = (int16_t)(counter0 & 0xFFFF);
        i2s0Buffers[buf0][1] = (int16_t)(counter0 >> 16);

        i2s1Buffers[buf1][0] = (int16_t)(counter1 & 0xFFFF);
        i2s1Buffers[buf1][1] = (int16_t)(counter1 >> 16);

        // Copy actual samples
        memcpy(i2s0Buffers[buf0] + 2, temp0, bytesRead0);
        memcpy(i2s1Buffers[buf1] + 2, temp1, bytesRead1);

        // Queue items with index
        I2SBuffer msg0 = {buf0, 0, (samples0 + 2) * sizeof(int16_t)};
        I2SBuffer msg1 = {buf1, 1, (samples1 + 2) * sizeof(int16_t)};
        if (counter0 % 10 == 0)
        {
            if (xQueueSend(i2sQueue, &msg0, 0) != pdTRUE)
                printf("Drop I2S0 buffer %u\n", buf0);
        }

        if (xQueueSend(i2sQueue, &msg1, 0) != pdTRUE)
        {
            printf("Drop I2S1 buffer %u\n", buf1);
        }
        counter0++;
        counter1++;
    }
}
void mqttTask(void *param)
{
    const size_t batchBufferSize0 = (2048 + 2) * 3;
    const size_t batchBufferSize1 = (1024 + 2) * 3;
    static int16_t batchBuffer0[batchBufferSize0];
    static int16_t batchBuffer1[batchBufferSize1];

    size_t batchOffset0 = 0;
    size_t batchOffset1 = 0;

    while (true)
    {
        I2SBuffer msg;
        if (xQueueReceive(i2sQueue, &msg, portMAX_DELAY) == pdTRUE)
        {
            int16_t *src =
                (msg.which == 0)
                    ? i2s0Buffers[msg.index]
                    : i2s1Buffers[msg.index];

            size_t samples = msg.length / sizeof(int16_t);

            if (msg.which == 0)
            {
                // Flush batch if needed
                if (batchOffset0 + samples > batchBufferSize0)
                {
                    //mqtt.publish("I2S0", batchBuffer0, batchOffset0 * sizeof(int16_t));
                    batchOffset0 = 0;
                }

                memcpy(batchBuffer0 + batchOffset0, src, msg.length);
                batchOffset0 += samples;
            }
            else if (msg.which == 1)
            {
                // Flush batch if needed
                if (batchOffset1 + samples > batchBufferSize1)
                {
                    mqtt.publish("I2S1", batchBuffer1, batchOffset1 * sizeof(int16_t));
                    batchOffset1 = 0;
                }

                memcpy(batchBuffer1 + batchOffset1, src, msg.length);
                batchOffset1 += samples;
            }
            else
            {
                printf("MQTT task received invalid I2SBuffer message\n");
            }
        }
    }
}


extern "C" void app_main(void)
{
    setup();
    printf("Setup complete, starting tasks...\n");

    // Create I2S task on CPU1
    xTaskCreatePinnedToCore(i2sTask, "I2S_Task", 8192 * 2, nullptr, 5, nullptr, 1);

    // Create MQTT task on CPU0
    xTaskCreatePinnedToCore(mqttTask, "MQTT_Task", 4096 * 12, nullptr, 5, nullptr, 0);
}
