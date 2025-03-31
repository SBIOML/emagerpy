from control.interface_control import InterfaceControl
import time

def test_hand(hand_type, **kwargs):
    print(f"\n=== Testing {hand_type.capitalize()} Hand ===")
    try:
        # Initialize hand
        hand = InterfaceControl(hand_type=hand_type, **kwargs)
        
        # Connect to the device
        print(f"Connecting to {hand_type} hand...")
        hand.connect()
        
        # Test basic functionality
        print("\nTesting basic gestures...")
        gestures = ["fist", "open", "point", "peace"]
        for gesture in gestures:
            print(f"Sending gesture: {gesture}")
            hand.send_gesture(gesture)
            time.sleep(1)  # Wait between gestures
            
        # Test direct gesture interface
        print("\nTesting direct gesture interface...")
        for gesture_value in range(5):  # Test gestures 0-4
            print(f"Sending direct gesture value: {gesture_value}")
            hand.send_gesture(gesture_value, direct=True)
            time.sleep(0.5)
            
        # Test individual finger control
        print("\nTesting individual finger control...")
        fingers = [0, 1, 2, 3, 4]  # thumb to little finger
        for finger in fingers:
            print(f"Moving finger {finger} to position 50%")
            hand.send_finger_position(finger, 50)
            time.sleep(0.5)
            
        # Test hand-specific features
        if hand_type == "zeus":
            print("\nTesting telemetry...")
            hand.start_telemetry()
            time.sleep(2)
            hand.stop_telemetry()
            
        elif hand_type == "smart":
            # Test direct gesture interface
            print("\nTesting direct gesture interface...")
            for gesture_value in range(5):  # Test gestures 0-4
                print(f"Sending direct gesture value: {gesture_value}")
                hand.send_gesture(gesture_value, direct=True)
                time.sleep(0.5)
                
            # Test LED controls
            print("\nTesting LED controls...")
            hand.hand.toggle_led_rpi()
            time.sleep(1)
            hand.hand.blink_led_rpi()
            
        # Cleanup
        print("\nDisconnecting...")
        hand.disconnect()
        
    except Exception as e:
        print(f"Error testing {hand_type} hand: {e}")

def test_zeus_hand():
    test_hand("zeus")

def test_smart_hand():
    test_hand("smart", mode="BLE")

def test_psyonic_hand():
    test_hand("psyonic")

if __name__ == "__main__":
    print("Starting hand control tests...")
    
    # Test Zeus hand
    # test_zeus_hand()
    
    # Test psyonics hand
    test_psyonic_hand()
    
    # Wait between tests
    time.sleep(2)
    
    # Test Smart hand
    test_smart_hand()
    
    print("\nAll tests completed!") 