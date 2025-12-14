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

#define DATA_READY_GPIO GPIO_NUM_21 // safe, free

// SPI slave buffer for DMA transactions

#define SPI_MAX_CHUNK 4096

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

    //Enable pull-ups on SPI lines so we don't detect rogue pulses when no master is connected.
    gpio_set_pull_mode(SPI_MOSI, GPIO_PULLUP_ONLY);
    gpio_set_pull_mode(SPI_SCLK, GPIO_PULLUP_ONLY);
    gpio_set_pull_mode(SPI_CS, GPIO_PULLUP_ONLY);


    if (!initSPISlave())
    {
        printf("SPI slave init failed\n");
        while (1)
            ;
    }

    printf("Setup complete\n");
}

void spiSlaveTask(void *param)
{
    while (true)
    {
        uint8_t txBuffer[4096];
        for (int i = 0; i < sizeof(txBuffer); i++)
        {
            txBuffer[i] = i % 256; // Fill with sample data
        }

        spi_slave_transaction_t transmission = {};
        transmission.length = sizeof(txBuffer) * 8; // length in bits
        transmission.tx_buffer = txBuffer;
        transmission.rx_buffer = nullptr; // Not receiving data
        uint8_t ret = spi_slave_transmit(SPI_HOST_VAR, &transmission, portMAX_DELAY);
        if (ret != ESP_OK)
        {
            ESP_LOGE("SPI", "Payload transmit failed: %d", ret);
            break;
        }
    }
}

extern "C" void app_main(void)
{
    setup();
    printf("Setup complete, starting tasks...\n");

    xTaskCreatePinnedToCore(spiSlaveTask, "SPI_Slave_Task", 4096 * 4, nullptr, 5, nullptr, 0);
}
