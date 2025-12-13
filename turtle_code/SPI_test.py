import spidev
import struct
import time

# =======================
# SPI CONFIG
# =======================
SPI_BUS = 0
SPI_DEVICE = 0
SPI_SPEED_HZ = 10_000_000
SPI_MODE = 0
CHUNK_SIZE = 4096

# =======================
# I2S FORMAT
# =======================
COUNTER_SIZE = 4  # uint32
SAMPLE_SIZE = 2   # int16
BUFFER_SAMPLES = 1024
BUFFER_SIZE = COUNTER_SIZE + SAMPLE_SIZE * BUFFER_SAMPLES

I2S0_SIZE = COUNTER_SIZE + SAMPLE_SIZE * BUFFER_SAMPLES * 2  # stereo
I2S1_SIZE = COUNTER_SIZE + SAMPLE_SIZE * BUFFER_SAMPLES       # mono

# =======================
# SPI SETUP
# =======================
spi = spidev.SpiDev()
spi.open(SPI_BUS, SPI_DEVICE)
spi.max_speed_hz = SPI_SPEED_HZ
spi.mode = SPI_MODE

print("SPI master ready (request-per-chunk protocol)")

# =======================
# MAIN LOOP
# =======================
try:
    while True:
        # Request first chunk
        spi.xfer2([0x01])  # request next frame

        buf0 = [0x00] * CHUNK_SIZE
        buffer0 = spi.xfer2(buf0)  # skip the first byte (response to request)
        print(f"First four bytes of buffer0: {buffer0[:4]}")


        spi.xfer2([0x01])  # request next frame

        buf1 = [0x00] * CHUNK_SIZE
        buffer1 = spi.xfer2(buf1)  # skip the first byte (response to request)
    

        time.sleep(0.01)  # small delay between frames

except KeyboardInterrupt:
    print("Stopping SPI master...")
    spi.close()
