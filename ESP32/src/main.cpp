#include <Arduino.h>
#include "I2sInterface.hpp"
#include "MqttInterface.hpp"


// === Pin definitions ===

#define I2S0_BCLK  26
#define I2S0_LRCLK 25
#define I2S0_DIN   22

// Slave mode: SHARE the SAME clocks so must be wired togheter
#define I2S1_BCLK  16   // Must be 26
#define I2S1_LRCLK 4  // Must be 25
#define I2S1_DIN   32



// MIC 1 --> I2S0 channel 0 (left)
#define MIC1_SEL_PIN  13 // GPIO to select mic1 (if needed)
#define MIC1_SEL_VALUE 0 // Left channel
#define MIC1_SCK I2S0_BCLK // Clock on BCLK
#define MIC1_WS  I2S0_LRCLK // Word select on LRCLK
#define MIC1_DO I2S0_DIN // Data output from microphone to input for I2S0

// MIC 2 --> I2S0 channel 1 (right)
#define MIC2_SEL_PIN  14 // GPIO to select mic2 (if needed)
#define MIC2_SEL_VALUE 1 // Right channel
#define MIC2_SCK I2S0_BCLK // Clock on BCLK
#define MIC2_WS  I2S0_LRCLK // Word select on LRCLK
#define MIC2_DO I2S0_DIN // Data output from microphone to input for I2S0

// MIC 3 --> I2S1 channel 0 (left)
#define MIC3_SEL_PIN  27 // GPIO to select mic3 (if needed)
#define MIC3_SEL_VALUE 0 // Left channel
#define MIC3_SCK I2S1_BCLK // Clock on BCLK
#define MIC3_WS  I2S1_LRCLK // Word select on LRCLK
#define MIC3_DO I2S1_DIN // Data output from microphone to input for I2S1


#define SAMPLERATE 44100


//Create I2S interface objects
I2sInterface i2s0(I2S_NUM_0, I2S0_BCLK, I2S0_LRCLK, -1, I2S0_DIN, 
                  (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
                  I2S_BITS_PER_SAMPLE_16BIT,
                  I2S_CHANNEL_FMT_RIGHT_LEFT, SAMPLERATE);

I2sInterface i2s1(I2S_NUM_1, I2S1_BCLK, I2S1_LRCLK, -1, I2S1_DIN,
                  (i2s_mode_t)(I2S_MODE_SLAVE | I2S_MODE_RX),
                  I2S_BITS_PER_SAMPLE_16BIT,
                  I2S_CHANNEL_FMT_ONLY_LEFT, SAMPLERATE);

//MqttInterface mqtt("Havefun", "Havefun2", "10.250.34.201");


void setup() {
    Serial.begin(115200);
    delay(1000);


    pinMode(MIC1_SEL_PIN, OUTPUT);
    pinMode(MIC2_SEL_PIN, OUTPUT);
    pinMode(MIC3_SEL_PIN, OUTPUT);


    // Select microphones
    digitalWrite(MIC1_SEL_PIN, MIC1_SEL_VALUE);
    digitalWrite(MIC2_SEL_PIN, MIC2_SEL_VALUE);
    digitalWrite(MIC3_SEL_PIN, MIC3_SEL_VALUE);




    // Initialize both I2S peripherals
    if (i2s0.begin()) {
        Serial.println("I2S0 initialized (stereo mic1+mic2)");
    } else {
        Serial.println("Failed to initialize I2S0");
    }

    delay(1000);

    if (i2s1.begin()) {
        Serial.println("I2S1 initialized (mono mic3)");
    } else {
        Serial.println("Failed to initialize I2S1");
    }
    //mqtt.begin();
    //mqtt.overrideMaxBufferSize(1024 * 4 + 512); // Increase MQTT buffer to 1024 * 4 bytes for 2 channels and stereo + some extra margin

}






void loop() {
    //mqtt.loop();
    const int numSamples = 1024*8;

    // Reserve space for: [counter(4 bytes)] + audio samples
    static int16_t buffer0[numSamples * 2 + 2]; 
    static int16_t buffer1[numSamples + 2];

    static uint32_t counter = 0;

    // Audio starts after first 2 int16 = 4 bytes
    int16_t* audioBufferPtr0 = buffer0 + 2;
    int16_t* audioBufferPtr1 = buffer1 + 2;


    // Read stereo samples
    size_t bytesRead0 = i2s0.readSamples(
        audioBufferPtr0,
        numSamples * 2 * sizeof(int16_t)
    );


    // Read mono samples
    size_t bytesRead1 = i2s1.readSamples(
        audioBufferPtr1,
        numSamples * sizeof(int16_t)
    );

    // Write counter (4 bytes) into first 2 int16 positions
    memcpy(buffer0, &counter, sizeof(counter));
    memcpy(buffer1, &counter, sizeof(counter));

    counter++;

    if (counter == 20){
        Serial.println("Buffer0:");
        for (int i = 0; i < sizeof(buffer0)/sizeof(buffer0[0]); i++){
            Serial.print(buffer0[i]);
            if (i < sizeof(buffer0)/sizeof(buffer0[0]) -1)
                Serial.print(", ");
        }
        Serial.println();
        Serial.println("Buffer1:");
        for (int i = 0; i < sizeof(buffer1)/sizeof(buffer1[0]); i++){
            Serial.print(buffer1[i]);
            if (i < sizeof(buffer1)/sizeof(buffer1[0]) -1)
                Serial.print(", ");
        }
        Serial.println();
    }


    //mqtt.publish("I2S0", (uint8_t*)buffer0, sizeof(buffer0));
    //mqtt.publish("I2S1", (uint8_t*)buffer1, sizeof(buffer1));
}
