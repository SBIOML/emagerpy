from control.interface_control import HandInterface
from control.serial_com import SerialCommunication
from control.gesture_decoder import decode_gesture
import time
import struct
from enum import Enum

FRAME_CHAR = 0x7E
ESC_CHAR = 0x7D
MASK_CHAR = 0x20

class PsyonicHandControl(HandInterface):
    # Protocol constants
    
    # Command types
    CMD_INIT = 0x01
    CMD_FINGER_POS = 0x10
    
    def __init__(self, address=0x50, baudrate=460800, port=None, stuffing=True):
        """
        Initialize the Psyonic hand controller.
        
        Args:
            baudrate (int): Serial communication baudrate (default: 115200)
            port (str): Serial port to connect to (e.g., 'COM3' on Windows)
                       If None, will try to auto-detect USB to TTL device
        """
        self.address = address
        self.port = port
        self.baudrate = baudrate
        self.serial = None
        self.connected = False
        self.stuffing = stuffing

    def connect(self):
        """Connect to the Psyonic hand via serial communication."""
        if self.connected:
            return
            
        try:
            print(f"Connecting to Psyonic hand via USB to TTL on {self.port}")
            self.serial = SerialCommunication(port=self.port, baud_rate=self.baudrate)
            self.serial.open()
            self.connected = True
            print(f"Connected to Psyonic hand on {self.serial.port}")
            
            # Initialize the hand
            self._send_init_command()
            
        except Exception as e:
            print(f"Error connecting to Psyonic hand: {e}")
            print("Make sure connections are correct:")
            print("  TX (USB to TTL) → RX (Psyonic hand)")
            print("  RX (USB to TTL) → TX (Psyonic hand)")
            print("  GND (USB to TTL) → GND (Psyonic hand)")
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
        NEEDS TO BE FIXED (need all prior finger positions)
        
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
        
    def read_data(self):
        """Read a packet from the Psyonic hand."""
        packet = self.serial.read()
        if self.stuffing:
            ppp = PPPUnstuff()
            unstuffed_packet = ppp.unstuff_packet(packet)
        else:
            unstuffed_packet = packet

        return unstuffed_packet

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
        
        # Create packet header
        packet = bytearray([self.address, cmd_type])
        
        # Add payload
        packet.extend(payload)
        
        # Calculate and add checksum
        checksum = (-sum(packet[1:])) & 0xFF
        packet.append(checksum)
        
        return packet

    def _send_packet(self, packet):
        """Send a packet with PPP stuffing."""
        if self.stuffing:
            stuffed_packet = ppp_stuff(packet)
        else:
            stuffed_packet = packet
        
        self.serial.write(stuffed_packet)
        time.sleep(0.1)  # Small delay to ensure command is processed

    def _send_init_command(self):
        """Send initialization command to the Psyonic hand."""
        # Create init packet
        packet = self._create_packet(self.CMD_INIT, b'')
        self._send_packet(packet)
        time.sleep(1)  # Wait for initialization to complete
        

def ppp_stuff(array: bytearray | bytes) -> bytearray:
    """Stuffing involves adding a FRAME_CHAR 0x7E '~' to the begining and end of
    a frame and XOR'ing any bytes with MASK_CHAR 0x20 that equal the FRAME/ESC
    char.  This allows you to determine the beginning and end of a frame and not
    have FRAME_CHAR or ESC_CHAR that are actually in the data confuse the parsing
    of the frame"""

    # Find ESC and FRAME chars
    ind = [i for i, v in enumerate(array) if v == ESC_CHAR or v == FRAME_CHAR]

    for i in ind:  # Mask Chars
        array[i] = array[i] ^ MASK_CHAR

    # Insert ESC char in front of masked char reverse to prevent index mess up
    for i in sorted(ind, reverse=True):
        array.insert(i, ESC_CHAR)

    array.insert(0, FRAME_CHAR)  # Mark beginning of frame
    array.append(FRAME_CHAR)  # Mark end of the frame

    return array

class PPPState(Enum):
    START_FRAME = 0
    DATA = 1
    END_FRAME = 2


class PPPUnstuff:
    def __init__(self, buffer_size=512):
        self.state = PPPState.START_FRAME
        self.buffer_size = buffer_size
        self.buffer = bytearray(buffer_size)
        self.idx = 0
        self.unmask_next_char = False

    def reset_state(self):
        self.state = PPPState.START_FRAME
        self.idx = 0

    def add_to_buffer(self, byte: int):
        if self.idx >= self.buffer_size:
            print("Exceeded maximum buffer size")
            self.reset_state()
        else:
            self.buffer[self.idx] = byte
            self.idx += 1

    def unstuff_byte(self, byte: int) -> None | bytearray:
        """Stateful byte parser for unstuffing PPP stuffed frames.  Unstuffing
        simply require you to remove the FRAME_CHAR 0x20 '~' byte from the end
        and beginning of the frame, it also requires removing any ESC_CHAR
        characters 0x7D (NOT ASCII) and XOR bytes that follow ESC_CHARS with
        MASK_CHAR 0x20.  This is required if the frame contains a FRAME_CHAR or
        ESC_CHAR not intended to be used for stuffing. Really only needs to be a
        one state state machine, read data, or don't, but state machine helps
        with readability and understanding the if statements"""
        if byte != FRAME_CHAR:
            # If we see a non frame char and not in a reading data state, skip
            if self.state != PPPState.DATA:
                return None
        else:
            if self.idx > 0:
                # We are at the end of a frame because we have data
                self.state = PPPState.END_FRAME  # Just here for readability
                idx_copy = self.idx  # Annoying...
                self.reset_state()  # Resets idx and sets state to start
                return bytearray(
                    self.buffer[0:idx_copy]
                )  # Creates a copy because it would definitely suck if we read a byte before processing the returned byte array
            else:
                # We are at the beginning of a frame
                self.reset_state()
                self.state = PPPState.DATA
                return None
        if (
            byte == ESC_CHAR
        ):  # Next byte needs to be unmasked, next byte will never be FRAME_CHAR
            self.unmask_next_char = True
            return None
        if self.unmask_next_char:
            byte ^= MASK_CHAR
            self.unmask_next_char = False

        # Data read state
        if self.state == PPPState.DATA:
            self.add_to_buffer(byte)
            return None
        
    def unstuff_packet(self, packet: bytearray | bytes) -> bytearray:
        """Unstuff a packet."""
        for byte in packet:
            self.unstuff_byte(byte)
        return self.buffer
