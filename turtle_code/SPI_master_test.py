import spidev
import struct
import time

class SPIAudioMaster:
    def __init__(self, debug=True):  # DEBUG ON BY DEFAULT
        self.spi = spidev.SpiDev()
        self.spi.open(0, 0)
        self.spi.max_speed_hz = 1000000
        self.spi.mode = 0
        self.debug = debug
        
        # Clear any garbage on the line
        self._clear_spi_line()
    
    def _clear_spi_line(self):
        """Clear any partial data on SPI line"""
        print("Clearing SPI line...")
        for _ in range(10):
            self.spi.xfer2([0x00])
            time.sleep(0.001)
    
    def query_available(self):
        """Ask ESP32 how many packets are ready"""
        print("\n--- Sending QUERY (0x01) ---")
        response = self.spi.xfer2([0x01, 0x00, 0x00])
        
        print(f"Raw response: {response}")
        print(f"Hex response: {[hex(x) for x in response]}")
        
        # Accept ONLY 0x81 (not 0x8f)
        if response[0] == 0x81:
            available_count = response[1]
            print(f"✓ ESP32 reports {available_count} packets ready")
            return available_count
        elif response[0] == 0xFF:
            error = response[1]
            print(f"✗ ESP32 error: code 0x{error:02x}")
            return 0
        else:
            print(f"✗ Unexpected header: 0x{response[0]:02x} (expected 0x81)")
            print(f"  This means ESP32 is NOT sending correct query response!")
            return 0
    
    def request_next_packet(self):
        """Request the next available packet"""
        print("\n--- Requesting packet (sending 0x02) ---")
        
        # 1. Send request command
        self.spi.xfer2([0x02])
        
        # 2. Read Frame 1 (4096 bytes)
        print("Reading Frame 1 (4096 bytes)...")
        frame1 = self.spi.xfer2([0x00] * 4096)
        
        print(f"Frame 1 header: 0x{frame1[0]:02x}")
        print(f"First 16 bytes: {[hex(x) for x in frame1[:16]]}")
        
        if frame1[0] == 0xFF:
            print(f"ESP32 error in frame 1: 0x{frame1[1]:02x}")
            return None
        
        if frame1[0] != 0x01:
            print(f"⚠️ Warning: Expected 0x01, got 0x{frame1[0]:02x}")
            print("  Will try to read Frame 2 anyway...")
        
        # 3. Read Frame 2 (2058 bytes)
        print("Reading Frame 2 (2058 bytes)...")
        frame2 = self.spi.xfer2([0x00] * 2058)
        
        print(f"Frame 2 header: 0x{frame2[0]:02x}")
        print(f"Frame 2 first 8 bytes: {[hex(x) for x in frame2[:8]]}")
        
        # Extract ID regardless of header
        packet_id = 0
        if len(frame2) >= 3:
            packet_id = (frame2[2] << 8) | frame2[1]
            print(f"Packet ID from bytes [{frame2[1]:02x}, {frame2[2]:02x}]: {packet_id}")
        
        # Reassemble
        frame1_data = frame1[1:4096]  # Bytes 1-4095
        frame2_data = frame2[3:] if len(frame2) > 3 else b''
        full_packet = frame1_data + frame2_data
        
        print(f"Reassembled: {len(full_packet)} bytes")
        
        if len(full_packet) >= 8:
            # Try to extract counters
            try:
                counter0 = struct.unpack('<I', bytes(full_packet[0:4]))[0]
                counter1 = struct.unpack('<I', bytes(full_packet[4:8]))[0]
                
                print(f"✓ Packet {packet_id}: Counter0={counter0}, Counter1={counter1}")
                print(f"  Audio data: {len(full_packet[8:])} bytes")
                
                return {
                    'id': packet_id,
                    'counter0': counter0,
                    'counter1': counter1,
                    'audio': full_packet[8:],
                    'full_data': full_packet
                }
            except:
                print("✗ Could not unpack counters (bad data)")
                # Print raw bytes
                print(f"First 16 bytes of packet: {[hex(x) for x in full_packet[:16]]}")
        
        return None
    
    def simple_test(self):
        """Run a simple test sequence"""
        print("\n" + "="*60)
        print("SIMPLE TEST - Step by Step")
        print("="*60)
        
        # Step 1: Query
        count = self.query_available()
        
        if count > 0:
            print(f"\nTrying to receive {count} packets...")
            for i in range(min(3, count)):  # Try first 3 only
                print(f"\n--- Attempt {i+1} ---")
                packet = self.request_next_packet()
                if packet:
                    print(f"✓ SUCCESS: Got packet {packet['id']}")
                else:
                    print("✗ FAILED: No valid packet received")
        else:
            print("\nNo packets available. Check ESP32 I2S is running.")
        
        print("\n" + "="*60)

# Main execution
if __name__ == "__main__":
    print("SPI Audio Master - DEBUG MODE")
    print("Connecting to ESP32...")
    
    master = SPIAudioMaster(debug=True)
    master.simple_test()