#!/usr/bin/env python3
"""
HITBOT eHand-6 Index Finger Manual Movement Monitor
=====================================================
Disables motor torque and reads the position of the Index Finger (Motor 3)
in real-time to check if the encoder is physically responding to manual movement.
"""

import time
import sys
from ehand_driver import EHand6Driver, HandID

def main():
    driver = EHand6Driver(channel='can0', hand_id=HandID.RIGHT)
    try:
        driver.connect()
    except Exception as e:
        print(f"✗ Failed to connect to CAN bus: {e}")
        sys.exit(1)
        
    print("\n1. Disabling motor torque to allow free manual movement...")
    driver.emergency_stop()  # Sends disabled mode
    time.sleep(1.0)
    
    print("\n2. Monitoring Index Finger position in real-time.")
    print("   ---> Move the index finger manually now and observe if the position changes <---")
    print("   Press Ctrl+C to exit.")
    print("-" * 70)
    
    try:
        while True:
            status = driver.read_status()
            if status:
                idx = status.fingers.get("Index Finger")
                if idx:
                    # Print status
                    print(f"Pos: {idx.position_pct:5.1f}% ({idx.position:3d}) | State: {idx.state_name:12s} | Raw Byte 13: 0x{status.raw_data[12]:02X}")
                else:
                    print("Index Finger status not found in response.")
            else:
                print("No response from hand.")
            time.sleep(0.3)
    except KeyboardInterrupt:
        print("\nMonitoring stopped.")
    finally:
        driver.disconnect()

if __name__ == "__main__":
    main()
