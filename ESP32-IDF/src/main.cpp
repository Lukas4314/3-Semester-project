#include "I2sInterface.hpp"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "driver/spi_slave.h"
#include "esp_log.h"

// SPI pins
#define SPI_MISO GPIO_NUM_19
#define SPI_MOSI GPIO_NUM_23
#define SPI_SCLK GPIO_NUM_18
#define SPI_CS GPIO_NUM_5
#define SPI_HOST_VAR SPI2_HOST

// === Pin definitions ===
#define I2S0_BCLK GPIO_NUM_26
#define I2S0_LRCLK GPIO_NUM_25
#define I2S0_DIN GPIO_NUM_22
// #define I2S0_DIN GPIO_NUM_17

#define I2S1_BCLK GPIO_NUM_26
// #define I2S1_BCLK GPIO_NUM_16
#define I2S1_LRCLK GPIO_NUM_25
// #define I2S1_LRCLK GPIO_NUM_4
#define I2S1_DIN GPIO_NUM_32

#define MIC1_SEL_PIN GPIO_NUM_13
#define MIC1_SEL_VALUE 0
#define MIC2_SEL_PIN GPIO_NUM_14
#define MIC2_SEL_VALUE 1
#define MIC3_SEL_PIN GPIO_NUM_27
#define MIC3_SEL_VALUE 0

#define DATA_READY_GPIO GPIO_NUM_21 // safe, free

#define SAMPLE_RATE 16000
#define NUM_I2S_BUFFERS 10
#define BUFFER_SIZE 1024

QueueHandle_t i2sQueue;

#define BUFFER_SIZE_TOTAL (BUFFER_SIZE * 3 + 4)

static int16_t mic_data[NUM_I2S_BUFFERS][BUFFER_SIZE_TOTAL]; // 3 Mics

// SPI slave buffer for DMA transactions

#define SPI_MAX_CHUNK 4096

uint8_t spiHeader[4];
uint8_t spiSlaveBuf[SPI_MAX_CHUNK];
uint8_t spiSlaveBuf2[SPI_MAX_CHUNK];

static DRAM_ATTR I2sInterface i2s0;
static DRAM_ATTR I2sInterface i2s1;

bool ready = false;

struct I2SBuffer
{
    uint8_t index;
    size_t length; // bytes
};

// Called after a transaction is queued and ready for pickup by master. We use this to set the handshake line high.
void my_post_setup_cb(spi_slave_transaction_t *trans)
{
    gpio_set_level(DATA_READY_GPIO, 1);
}

// Called after transaction is sent/received. We use this to set the handshake line low.
void my_post_trans_cb(spi_slave_transaction_t *trans)
{
    gpio_set_level(DATA_READY_GPIO, 0);
}

// Initialize SPI as slave
bool initSPISlave()
{
    spi_bus_config_t buscfg = {};
    buscfg.miso_io_num = SPI_MISO;
    buscfg.mosi_io_num = SPI_MOSI;
    buscfg.sclk_io_num = SPI_SCLK;
    buscfg.quadhd_io_num = -1;
    buscfg.quadwp_io_num = -1;
    buscfg.max_transfer_sz = SPI_MAX_CHUNK;

    spi_slave_interface_config_t slvcfg = {};
    slvcfg.spics_io_num = SPI_CS;
    slvcfg.queue_size = 3;
    slvcfg.mode = 0; // SPI mode 0
    slvcfg.flags = 0;
    slvcfg.post_setup_cb = my_post_setup_cb;
    slvcfg.post_trans_cb = my_post_trans_cb;

    esp_err_t ret = spi_slave_initialize(SPI_HOST_VAR, &buscfg, &slvcfg, 1);
    if (ret != ESP_OK)
    {
        ESP_LOGE("SPI", "Slave init failed: %d", ret);
        return false;
    }
    return true;
}

// Setup function
void setup()
{

    // Configure as output
    gpio_config_t io_conf = {};
    io_conf.intr_type = GPIO_INTR_DISABLE;
    io_conf.mode = GPIO_MODE_OUTPUT;
    io_conf.pin_bit_mask = BIT64(DATA_READY_GPIO);
    gpio_config(&io_conf);

    // Default LOW
    gpio_set_level(DATA_READY_GPIO, 0);

    // Enable pull-ups on SPI lines so we don't detect rogue pulses when no master is connected.
    gpio_set_pull_mode(SPI_MOSI, GPIO_PULLUP_ONLY);
    gpio_set_pull_mode(SPI_SCLK, GPIO_PULLUP_ONLY);
    gpio_set_pull_mode(SPI_CS, GPIO_PULLUP_ONLY);

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
    i2s1 = I2sInterface(I2S_NUM_1, I2S_ROLE_SLAVE, I2S_DATA_BIT_WIDTH_16BIT,
                        I2S_SLOT_MODE_STEREO, GPIO_NUM_NC, I2S1_BCLK, I2S1_LRCLK, I2S1_DIN,
                        I2S_STD_SLOT_BOTH, SAMPLE_RATE, 1);

    i2sQueue = xQueueCreate(NUM_I2S_BUFFERS - 1, sizeof(I2SBuffer));

    printf("Setup complete\n");

    if (!i2s1.begin())
    {
        printf("I2S1 init failed\n");
        while (1)
            ;
    }

    if (!i2s0.begin())
    {
        printf("I2S0 init failed\n");
        while (1)
            ;
    }
}

// I2S capture task
void i2sTask(void *param)
{
    uint32_t counter0 = 0;
    uint32_t counter1 = 0;
    uint8_t i2s0Idx = 0;

    const size_t stereoSize = BUFFER_SIZE * 2;
    const size_t monoSize = BUFFER_SIZE;

    static int16_t temp0[stereoSize];
    static int16_t temp1[monoSize];
    static int16_t tempTemp[stereoSize]; // to help with mono extraction

    while (true)
    {
        size_t bytesRead0 = i2s0.readSamples(temp0, stereoSize * sizeof(int16_t));
        size_t bytesRead1 = i2s1.readSamples(tempTemp, stereoSize * sizeof(int16_t));
        for (size_t i = 0; i < BUFFER_SIZE; i++)
        {
            // Extract mono from stereo (left channel)
            temp1[i] = tempTemp[i * 2];
        }

        int offset = 100;
        //printf("%d %d %d    |||     %d %d %d    |||    %d %d %d\n",
        //       temp0[offset + 0], temp0[offset + 2], temp0[offset + 4], temp0[offset + 1], temp0[offset + 3], temp0[offset + 5],
        //       temp1[offset + 0], temp1[offset + 1], temp1[offset + 2]);
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

        memcpy(mic_data[buf0] + 2, temp0, bytesRead0);
        memcpy(mic_data[buf0] + BUFFER_SIZE * 2 + 4, temp1, monoSize * sizeof(int16_t));

        offset += 2;
        printf("%d %d %d    |||     %d %d %d    |||    %d %d %d\n",
               mic_data[buf0][offset + 0], mic_data[buf0][offset + 2], mic_data[buf0][offset + 4],
               mic_data[buf0][offset + 1], mic_data[buf0][offset + 3], mic_data[buf0][offset + 5],
               mic_data[buf0][offset + 0 + BUFFER_SIZE * 2 + 2], mic_data[buf0][offset + 1 + BUFFER_SIZE * 2 + 2], mic_data[buf0][offset + 2 + BUFFER_SIZE * 2 + 2]);

        // Queue buffers for SPI task
        I2SBuffer msg0 = {buf0, (bytesRead0 + 4 + monoSize * sizeof(int16_t) + 4)}; // 2 counters * 2 bytes

        uint8_t err = xQueueSend(i2sQueue, &msg0, 0);
        if (err != pdTRUE)
        {
            // Queue full, overflow
            printf("Queue full, idx dropped: %d\n", buf0);
        }

        counter0++;
        counter1++;
    }
}

void spiSlaveTask(void *param)
{
    if (!initSPISlave())
    {
        printf("SPI slave init failed\n");
        while (1)
            ;
    }
    while (true)
    {
        I2SBuffer msg;

        if (xQueueReceive(i2sQueue, &msg, portMAX_DELAY) == pdTRUE)
        {
            int16_t *src = mic_data[msg.index];
            uint16_t payload_len = msg.length; // bytes

            spi_slave_transaction_t t = {};
            uint32_t remaining = payload_len;
            // printf("SPI Slave sending buffer idx %d, length %d bytes\n", msg.index, payload_len);
            uint8_t *byte_src = (uint8_t *)src;

            while (remaining > 0)
            {

                uint32_t chunk = remaining > SPI_MAX_CHUNK ? SPI_MAX_CHUNK : remaining;

                memcpy(spiSlaveBuf, byte_src, chunk);

                t.length = chunk * 8;
                t.tx_buffer = spiSlaveBuf;
                t.rx_buffer = NULL;

                // Print the number in the middle of the payload to make sure it is not all 0
                // printf("SPI Slave transmitting chunk, first bytes: %d %d %d %d ... middle bytes: %d %d %d %d ... last bytes: %d %d %d %d\n",
                //       spiSlaveBuf[0], spiSlaveBuf[1], spiSlaveBuf[2], spiSlaveBuf[3],
                //       spiSlaveBuf[chunk / 2], spiSlaveBuf[chunk / 2 + 1], spiSlaveBuf[chunk / 2 + 2], spiSlaveBuf[chunk / 2 + 3],
                //       spiSlaveBuf[chunk - 4], spiSlaveBuf[chunk - 3], spiSlaveBuf[chunk - 2], spiSlaveBuf[chunk - 1]);

                uint8_t ret = spi_slave_transmit(SPI_HOST_VAR, &t, portMAX_DELAY);
                if (ret != ESP_OK)
                {
                    ESP_LOGE("SPI", "Payload transmit failed: %d", ret);
                    break;
                }

                byte_src += chunk;
                remaining -= chunk;
                vTaskDelay(pdMS_TO_TICKS(15)); // small delay to allow master to process data since it does not work otherwise (not sure why)
            }
        }
    }
}

extern "C" void app_main(void)
{
    setup();
    printf("Setup complete, starting tasks...\n");

    xTaskCreatePinnedToCore(i2sTask, "I2S_Task", 8192 * 3, nullptr, 5, nullptr, 1);
    xTaskCreatePinnedToCore(spiSlaveTask, "SPI_Slave_Task", 4096 * 4, nullptr, 5, nullptr, 0);
}
