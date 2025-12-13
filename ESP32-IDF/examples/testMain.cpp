#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/spi_slave.h"
#include "esp_log.h"
#include "esp_system.h"
#include "driver/gpio.h"

// SPI pins
#define SPI_MISO GPIO_NUM_19
#define SPI_MOSI GPIO_NUM_23
#define SPI_SCLK GPIO_NUM_18
#define SPI_CS GPIO_NUM_5
#define SPI_HOST_VAR SPI2_HOST
#define DATA_READY_GPIO GPIO_NUM_21 // safe, free

#define SPI_MAX_CHUNK 4096

static uint8_t dummyData[SPI_MAX_CHUNK];

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
    gpio_set_level(DATA_READY_GPIO, 1);
    esp_err_t ret = spi_slave_initialize(SPI_HOST_VAR, &buscfg, &slvcfg, 1);
    if (ret != ESP_OK)
    {
        ESP_LOGE("SPI", "Slave init failed: %d", ret);
        return false;
    }
    gpio_set_level(DATA_READY_GPIO, 1);

    return true;
}

void spiTask(void *param)
{
    uint8_t counter = 0;
    while (true)
    {
        // Fill dummy data
        for (int i = 0; i < SPI_MAX_CHUNK-1; i++)
            dummyData[i] = i & 0xFF;
        dummyData[0] = counter;
        counter++;
        spi_slave_transaction_t t = {};
        t.length = SPI_MAX_CHUNK * 8; // bits
        t.tx_buffer = dummyData;
        t.rx_buffer = NULL;

        gpio_set_level(DATA_READY_GPIO, 1);

        esp_err_t ret = spi_slave_transmit(SPI_HOST_VAR, &t, portMAX_DELAY);
        if (ret != ESP_OK)
        {
            ESP_LOGE("SPI", "Transmit failed: %d", ret);
        }
        else
        {
            ESP_LOGI("SPI", "Dummy chunk sent!");
        }
        gpio_set_level(DATA_READY_GPIO, 0);

        vTaskDelay(pdMS_TO_TICKS(500)); // send every 500 ms
    }
}

extern "C" void app_main(void)
{
    if (!initSPISlave())
    {
        ESP_LOGE("MAIN", "SPI Slave init failed, halting...");
        while (true)
            ;
    }

    // Configure as output
    gpio_config_t io_conf = {};
    io_conf.pin_bit_mask = 1ULL << DATA_READY_GPIO;
    io_conf.mode = GPIO_MODE_OUTPUT;
    io_conf.pull_down_en = GPIO_PULLDOWN_DISABLE;
    io_conf.pull_up_en = GPIO_PULLUP_DISABLE;
    gpio_config(&io_conf);
    // Default LOW
    gpio_set_level(DATA_READY_GPIO, 0);

    xTaskCreatePinnedToCore(spiTask, "SPI_Task", 4096, nullptr, 5, nullptr, 0);
}
