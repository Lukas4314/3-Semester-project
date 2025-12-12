#include "I2sInterface.hpp"
#include "MqttInterface.hpp"
#include "esp_timer.h"
#include "esp_memory_utils.h"

// === Pin definitions ===

#define I2S0_BCLK  GPIO_NUM_26
#define I2S0_LRCLK GPIO_NUM_25
#define I2S0_DIN   GPIO_NUM_22

// Slave mode: SHARE the SAME clocks so must be wired togheter
#define I2S1_BCLK  GPIO_NUM_16   // Must be 26
#define I2S1_LRCLK GPIO_NUM_4  // Must be 25
#define I2S1_DIN   GPIO_NUM_32



// MIC 1 --> I2S0 channel 0 (left)
#define MIC1_SEL_PIN  GPIO_NUM_13 // GPIO to select mic1 (if needed)
#define MIC1_SEL_VALUE 0 // Left channel
#define MIC1_SCK I2S0_BCLK // Clock on BCLK
#define MIC1_WS  I2S0_LRCLK // Word select on LRCLK
#define MIC1_DO I2S0_DIN // Data output from microphone to input for I2S0

// MIC 2 --> I2S0 channel 1 (right)
#define MIC2_SEL_PIN  GPIO_NUM_14 // GPIO to select mic2 (if needed)
#define MIC2_SEL_VALUE 1 // Right channel
#define MIC2_SCK I2S0_BCLK // Clock on BCLK
#define MIC2_WS  I2S0_LRCLK // Word select on LRCLK
#define MIC2_DO I2S0_DIN // Data output from microphone to input for I2S0

// MIC 3 --> I2S1 channel 0 (left)
#define MIC3_SEL_PIN  GPIO_NUM_27 // GPIO to select mic3 (if needed)
#define MIC3_SEL_VALUE 0 // Left channel
#define MIC3_SCK I2S1_BCLK // Clock on BCLK
#define MIC3_WS  I2S1_LRCLK // Word select on LRCLK
#define MIC3_DO I2S1_DIN // Data output from microphone to input for I2S1


#define SAMPLE_RATE 22050


MqttInterface mqtt("Havefun", "Havefun2", "mqtt://10.250.34.201");  // construct directly

static DRAM_ATTR I2sInterface i2s0;
static DRAM_ATTR I2sInterface i2s1;




void setup(){

    mqtt.begin();

    printf("Initialized MQTT interface...\n");

    
    // Set the pins to the correct l/r channel for each mic
    gpio_set_direction(MIC1_SEL_PIN, GPIO_MODE_OUTPUT);
    gpio_set_direction(MIC2_SEL_PIN, GPIO_MODE_OUTPUT);
    gpio_set_direction(MIC3_SEL_PIN, GPIO_MODE_OUTPUT);

    gpio_set_level(MIC1_SEL_PIN, MIC1_SEL_VALUE);
    gpio_set_level(MIC2_SEL_PIN, MIC2_SEL_VALUE);
    gpio_set_level(MIC3_SEL_PIN, MIC3_SEL_VALUE);




    i2s0 = I2sInterface(
        I2S_NUM_0,
        I2S_ROLE_MASTER,
        I2S_DATA_BIT_WIDTH_16BIT,
        I2S_SLOT_MODE_STEREO,
        GPIO_NUM_NC,    // MCLK
        I2S0_BCLK,    // BCLK
        I2S0_LRCLK,    // WS
        I2S0_DIN,    // DATA IN
        I2S_STD_SLOT_BOTH,
        SAMPLE_RATE,          // Sample Rate
        0                    // ID
    );

    i2s1 = I2sInterface(
        I2S_NUM_1,
        I2S_ROLE_SLAVE,
        I2S_DATA_BIT_WIDTH_16BIT,
        I2S_SLOT_MODE_MONO,
        GPIO_NUM_NC,    // MCLK
        I2S1_BCLK,    // BCLK
        I2S1_LRCLK,    // WS
        I2S1_DIN,    // DATA IN
        I2S_STD_SLOT_LEFT,
        SAMPLE_RATE,          // Sample Rate
        1                    // ID
    );


    printf("Initializing I2S interfaces...\n");

    
    if(!i2s1.begin()){
        printf("Failed to initialize I2S1");
        while(1);
    }

    if(!i2s0.begin()){
        printf("Failed to initialize I2S0");
        while(1);
    }

}

extern "C" void app_main(void)
{
    setup();
    printf("Setup complete, entering main loop.\n");
    uint32_t counter0 = 0;
    uint32_t counter1 = 0;


    while (true) {
        const uint16_t bufferSize = 1024;
        const size_t bufferSize0 = bufferSize*2; // Multiply by 2 for stereo
        const size_t bufferSize1 = bufferSize;

        static int16_t bufferWithCounter0[bufferSize0 + 2] = { (int16_t)(counter0 & 0xFFFF), (int16_t)((counter0 >> 16) & 0xFFFF) };
        static int16_t bufferWithCounter1[bufferSize1 + 2] = { (int16_t)(counter1 & 0xFFFF), (int16_t)((counter1 >> 16) & 0xFFFF) };

        static int16_t buffer0[bufferSize0];
        static int16_t buffer1[bufferSize1];


        size_t bytesRead0 = i2s0.readSamples(buffer0, bufferSize0*sizeof(int16_t));
        size_t bytesRead1 = i2s1.readSamples(buffer1, bufferSize1*sizeof(int16_t));

        if (i2s0.counterOffset != 0) {
            counter0 += i2s0.counterOffset;
            printf("I2S0 counter offset applied, offset was: %u\n", i2s0.counterOffset);
            i2s0.counterOffset = 0;
        }
        if (i2s1.counterOffset != 0) {
            counter1 += i2s1.counterOffset;
            printf("I2S1 counter offset applied, offset was: %u\n", i2s1.counterOffset);
            i2s1.counterOffset = 0;
        }

        
        memcpy(bufferWithCounter0 + 2, buffer0, bytesRead0);
        memcpy(bufferWithCounter1 + 2, buffer1, bytesRead1);

        //uint64_t start = esp_timer_get_time();  
        mqtt.publish("I2S0", bufferWithCounter0, bytesRead0 + 4); // +4 for counter
        mqtt.publish("I2S1", bufferWithCounter1, bytesRead1 + 4); // +4 for counter
        //uint64_t end = esp_timer_get_time();
        //printf("Elapsed: %llu us\n", end - start);
    }
}
