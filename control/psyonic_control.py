from control.interface_control import HandInterface
from control.serial_com import SerialCommunication
from control.gesture_decoder import decode_gesture
import time
import struct

class PsyonicHandControl(HandInterface):
    # Protocol constants
    FLAG_BYTE = 0x7E
    ESCAPE_BYTE = 0x7D
    ESCAPE_MASK = 0x20
    
    # Command types
    CMD_INIT = 0x01
    CMD_FINGER_POS = 0x02
    CMD_GESTURE = 0x03
    
    def __init__(self, baudrate=115200, port=None):
        """
        Initialize the Psyonic hand controller.
        
        Args:
            baudrate (int): Serial communication baudrate (default: 115200)
            port (str): Serial port to connect to (e.g., 'COM3' on Windows)
                       If None, will try to auto-detect USB to TTL device
        """
        self.port = port
        self.baudrate = baudrate
        self.serial = None
        self.connected = False

    def connect(self):
        """Connect to the Psyonic hand via serial communication."""
        if self.connected:
            return
            
        try:
            print(f"Connecting to Psyonic hand via USB to TTL on {self.port}")
            print("Make sure connections are correct:")
            print("  TX (USB to TTL) → RX (Psyonic hand)")
            print("  RX (USB to TTL) → TX (Psyonic hand)")
            print("  GND (USB to TTL) → GND (Psyonic hand)")
            
            self.serial = SerialCommunication(port=self.port, baud_rate=self.baudrate)
            self.serial.open()
            self.connected = True
            print(f"Connected to Psyonic hand on {self.serial.port}")
            
            # Initialize the hand
            self._send_init_command()
            
        except Exception as e:
            print(f"Error connecting to Psyonic hand: {e}")
            self.connected = False
            raise

    def disconnect(self):
        """Disconnect from the Psyonic hand."""
        if self.serial:
            self.serial.close()
            self.connected = False
            print("Disconnected from Psyonic hand")

    def send_gesture(self, gesture):
        """
        Send a gesture command to the Psyonic hand.
        
        Args:
            gesture (str): Name of the gesture to perform
        """
        if not self.connected:
            raise RuntimeError("Not connected to Psyonic hand")
            
        # Get finger positions from our gesture decoder
        thumb_pos, index_pos, middle_pos, ring_pos, little_pos = decode_gesture(gesture)
        
        # Scale positions from 0-1000 to 0-100 for Psyonic hand
        positions = [
            int(thumb_pos / 10),
            int(index_pos / 10),
            int(middle_pos / 10),
            int(ring_pos / 10),
            int(little_pos / 10)
        ]
        
        # Send all finger positions in one command
        self._send_finger_positions(positions)

    def send_finger_position(self, finger, position):
        """
        Send a specific finger position to the Psyonic hand.
        
        Args:
            finger (int): Finger index (0-4)
            position (int): Position value (0-100)
        """
        if not self.connected:
            raise RuntimeError("Not connected to Psyonic hand")
            
        if not 0 <= finger <= 4:
            raise ValueError("Finger index must be between 0 and 4")
            
        if not 0 <= position <= 100:
            raise ValueError("Position must be between 0 and 100")
            
        # Create positions array with only one finger set
        positions = [0] * 5
        positions[finger] = position
        self._send_finger_positions(positions)

    def _send_finger_positions(self, positions):
        """Send finger positions using the proper protocol."""
        # Create command payload
        payload = struct.pack('BBBBB', *positions)
        
        # Create command packet
        packet = self._create_packet(self.CMD_FINGER_POS, payload)
        
        # Send the packet
        self._send_packet(packet)

    def _create_packet(self, cmd_type, payload):
        """Create a properly formatted packet with checksum."""
        # Calculate packet length
        length = len(payload) + 2  # +2 for cmd_type and checksum
        
        # Create packet header
        packet = bytearray([self.FLAG_BYTE, length, cmd_type])
        
        # Add payload
        packet.extend(payload)
        
        # Calculate and add checksum
        checksum = sum(packet[1:]) & 0xFF
        packet.append(checksum)
        
        # Add closing flag
        packet.append(self.FLAG_BYTE)
        
        return packet

    def _send_packet(self, packet):
        """Send a packet with PPP stuffing."""
        stuffed_packet = bytearray()
        
        for byte in packet:
            if byte == self.FLAG_BYTE:
                stuffed_packet.extend([self.ESCAPE_BYTE, self.FLAG_BYTE ^ self.ESCAPE_MASK])
            elif byte == self.ESCAPE_BYTE:
                stuffed_packet.extend([self.ESCAPE_BYTE, self.ESCAPE_BYTE ^ self.ESCAPE_MASK])
            else:
                stuffed_packet.append(byte)
        
        self.serial.write(stuffed_packet)
        time.sleep(0.1)  # Small delay to ensure command is processed

    def _send_init_command(self):
        """Send initialization command to the Psyonic hand."""
        # Create init packet
        packet = self._create_packet(self.CMD_INIT, b'')
        self._send_packet(packet)
        time.sleep(1)  # Wait for initialization to complete
