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
        gestures = ["Peace", "Hand_Close", "Hand_Open", "OK"]
        for gesture in gestures:
            print(f"Sending gesture: {gesture}")
            hand.send_gesture(gesture)
            time.sleep(1)  # Wait between gestures
            
        # Test individual finger control
        print("\nTesting individual finger control...")
        fingers = [0, 1, 2, 3, 4]  # thumb to little finger
        for finger in fingers:
            print(f"Moving finger {finger} to position 50")
            hand.send_finger_position(finger, 100)
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
        raise e

if __name__ == "__main__":
    print("\n Starting hand control tests...")
    
    try:
        test_hand("psyonic", stuffing=True)
        print("\nAll tests completed!") 
    except Exception as e:
        print(f"Tests Failed! : {e}")
        
    
    