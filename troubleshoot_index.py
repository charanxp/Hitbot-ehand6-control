#!/usr/bin/env python3
"""
HITBOT eHand-6 Index Finger Diagnostic Script
==============================================
Runs diagnostics specifically on the Index Finger (Motor 3) to determine
if the issue is electrical, mechanical, or firmware-related.
"""

import time
import sys
from ehand_driver import EHand6Driver, HandID, ControlMode, FingerParams, MotorState, FaultCode

def monitor_status(driver: EHand6Driver, duration: float = 3.0, interval: float = 0.5):
    """Periodically read and print the index finger status."""
    start_time = time.time()
    while time.time() - start_time < duration:
        status = driver.read_status()
        if status:
            idx = status.fingers.get("Index Finger")
            if idx:
                print(f"  [{time.time()-start_time:3.1f}s] State: {idx.state_name:12s} | Pos: {idx.position_pct:5.1f}% ({idx.position:3d}) | Spd: {idx.speed_pct:5.1f}% | Fault: {idx.fault_name}")
            else:
                print("  Index Finger status not found in response.")
        else:
            print("  No response from hand.")
        time.sleep(interval)

def main():
    print("=" * 60)
    print("  HITBOT eHand-6 Index Finger (Motor 3) Diagnostics")
    print("=" * 60)
    
    driver = EHand6Driver(channel='can0', hand_id=HandID.RIGHT)
    
    try:
        driver.connect()
    except Exception as e:
        print(f"✗ Failed to connect to CAN bus: {e}")
        sys.exit(1)
        
    try:
        # 1. Read Initial Status
        print("\n1. Reading initial status...")
        status = driver.read_status()
        if not status:
            print("✗ Hand is not responding. Check cabling.")
            return
        
        idx = status.fingers.get("Index Finger")
        print(f"  Hand Machine State: {status.machine_state_name}")
        print(f"  Index Finger State: {idx.state_name}")
        print(f"  Index Finger Pos:   {idx.position_pct:.1f}% ({idx.position})")
        print(f"  Index Finger Spd:   {idx.speed_pct:.1f}% ({idx.speed})")
        print(f"  Index Finger Fault: {idx.fault_name}")
        
        # 2. Disable Motors (Release holding torque)
        print("\n2. Disabling all motors (releases mechanical hold)...")
        driver.emergency_stop()
        time.sleep(2.0)
        
        # 3. Try to Zero ONLY the Index Finger
        print("\n3. Sending ZERO/CALIBRATE command ONLY to Index Finger...")
        # Send zeroing mode specifically for Motor 3
        data = driver._build_control_frame(mode=ControlMode.ZEROING, motor_ids=[3])
        driver._send_frame(data)
        
        print("  Monitoring for 5 seconds during calibration...")
        monitor_status(driver, duration=5.0, interval=0.5)
        
        # 4. Try to send a small movement command (50% position)
        print("\n4. Trying to command Index Finger to 50% position...")
        # Control mode 1 (Position), Motor 3, Pos=128, Spd=128, Trq=204
        fingers = {3: FingerParams(position=128, speed=128, torque=204)}
        data = driver._build_control_frame(mode=ControlMode.POSITION, fingers=fingers, motor_ids=[3])
        driver._send_frame(data)
        
        print("  Monitoring for 3 seconds during position command...")
        monitor_status(driver, duration=3.0, interval=0.5)
        
        # 5. Disable again for safety
        print("\n5. Disabling motors for safety...")
        driver.emergency_stop()
        
    except KeyboardInterrupt:
        print("\nInterrupted.")
        driver.emergency_stop()
    finally:
        driver.disconnect()
        print("\nDiagnostics complete.")
        print("=" * 60)

if __name__ == "__main__":
    main()
