import spidev
import struct
import time
from RPi import GPIO
import queue

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

I2S0_SIZE = COUNTER_SIZE + SAMPLE_SIZE * BUFFER_SAMPLES * 2 # Times 2 for both channels
I2S1_SIZE = COUNTER_SIZE + SAMPLE_SIZE * BUFFER_SAMPLES

EXTRA_BYTES = 2 * CHUNK_SIZE - (I2S0_SIZE + I2S1_SIZE)

# =======================
# DATA_READY PIN
# =======================
DATA_READY_PIN = 17  # Pi GPIO connected to ESP32 DATA_READY

# =======================
# SPI SETUP
# =======================
spi = spidev.SpiDev()
spi.open(SPI_BUS, SPI_DEVICE)
spi.max_speed_hz = SPI_SPEED_HZ
spi.mode = SPI_MODE

print("SPI master ready (framed protocol)")





# Queue for non-blocking callback
frame_queue = queue.Queue()

# =======================
# DATA_READY CALLBACK
# =======================
def data_ready_callback(channel):
    """Non-blocking callback: just push an event to the queue."""
    frame_queue.put(True)



# =======================
# LGPIO INITIALIZATION
# =======================
# Choose BCM numbering (you can also use GPIO.BOARD)
GPIO.setmode(GPIO.BCM)
GPIO.setup(DATA_READY_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.add_event_detect(DATA_READY_PIN, GPIO.RISING, callback=data_ready_callback)



# =======================
# MAIN LOOP
# =======================
try:
    print("Waiting for DATA_READY signals from ESP32...")
    while True:
        try:
            # Wait for an event (timeout avoids blocking shutdown)
            frame_queue.get(block=True)
            buffer0 = spi.xfer2([0x00] * CHUNK_SIZE)  
            
            frame_queue.get(block=True)
            buffer1 = spi.xfer2([0x00] * CHUNK_SIZE)
            whole_buffer = buffer0 + buffer1
            if len(whole_buffer) != I2S0_SIZE + I2S1_SIZE + EXTRA_BYTES:
                print(f"Warning: Expected {I2S0_SIZE + I2S1_SIZE + EXTRA_BYTES} bytes, got {len(whole_buffer)} bytes")
            whole_buffer = whole_buffer[:I2S0_SIZE + I2S1_SIZE]  # Discard extra bytes
            #print(f"whole_buffer: {whole_buffer}")
            I2S0_bytes = whole_buffer[:I2S0_SIZE]
            I2S1_bytes = whole_buffer[I2S0_SIZE:]
            #print(f"First 16 bytes of I2S0: {I2S0_bytes[:16]}")
            #print(f"First 16 bytes of I2S1: {I2S1_bytes[:16]}")
            counter_bytes0 = I2S0_bytes[:COUNTER_SIZE]
            counter_bytes1 = I2S1_bytes[:COUNTER_SIZE]
            counter0 = struct.unpack('<I', bytes(counter_bytes0))[0]
            counter1 = struct.unpack('<I', bytes(counter_bytes1))[0]
            print(f"Received frame with counters: I2S0={counter0}, I2S1={counter1}")

        except queue.Empty:
            # No event, loop again
            pass

except KeyboardInterrupt:
    print("Stopping SPI master...")
    GPIO.cleanup()
    spi.close()
