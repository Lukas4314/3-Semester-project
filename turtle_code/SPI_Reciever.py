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
# FRAME FORMAT
# =======================
FRAME_HEADER = b'\xAA\x55'
HEADER_SIZE = 4  # 2 bytes header + 2 bytes length

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

# =======================
# SPI HELPERS
# =======================
def spi_read_exact(spi, nbytes):
    """Clock exactly nbytes from SPI slave."""
    buf = bytearray()
    remaining = nbytes

    while remaining > 0:
        n = min(remaining, CHUNK_SIZE)
        buf.extend(spi.xfer2([0x00] * n))
        remaining -= n

    return bytes(buf)


def spi_read_frame(spi):
    """Reads one framed SPI packet: [0xAA 0x55][uint16 payload_len][payload]"""
    # Step 1: Find frame header
    sync = bytearray()
    while True:
        byte = spi.xfer2([0x00])[0]
        print(f"Read byte: {byte:02X}")
        sync.append(byte)
        if len(sync) > 2:
            sync.pop(0)
        if bytes(sync) == FRAME_HEADER:
            break

    # Step 2: Read payload length (uint16 LE)
    length_bytes = spi_read_exact(spi, 2)
    payload_len = struct.unpack('<H', length_bytes)[0]

    # Step 3: Read payload
    payload = spi_read_exact(spi, payload_len)
    return payload


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
            frame_queue.get(timeout=1)
            payload = spi_read_frame(spi)

            if len(payload) % 2 == 0:
                samples = struct.unpack('<' + 'h' * (len(payload) // 2), payload)
                print(f"Received frame: {len(samples)} samples")
            else:
                print(f"Received frame: {len(payload)} bytes (unaligned)")

        except queue.Empty:
            # No event, loop again
            pass

except KeyboardInterrupt:
    print("Stopping SPI master...")
    GPIO.cleanup()
    spi.close()
