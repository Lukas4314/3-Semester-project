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
SPI_SPEED_HZ = 5_000_000
SPI_MODE = 0
CHUNK_SIZE = 4096

DATA_READY_PIN = 17 # Pi GPIO connected to ESP32 DATA_READY

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





# Queue for non-blocking callback 
frame_queue = queue.Queue() 
# # ======================= 
# # DATA_READY CALLBACK 
# # ======================= 
def data_ready_callback(channel): 
# """Non-blocking callback: just push an event to the queue.""" 
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
    while True:
        # Request first chunk
        frame_queue.get()  # wait for DATA_READY signal
        values = spi.readbytes(CHUNK_SIZE)
        print(f"First four bytes of chunk: {values[:4]}")
        
        time.sleep(0.01)  # small delay between frames

except KeyboardInterrupt:
    print("Stopping SPI master...")
    spi.close()
