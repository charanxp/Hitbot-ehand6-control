#!/usr/bin/env python3
"""
HITBOT eHand-6 LinkedIn Video Demo Script
===========================================
This script runs a fluid, coordinated sequence of movements using the 5 WORKING
fingers (Thumb Horizontal, Thumb Vertical, Middle, Ring, and Little).

It specifically bypasses Motor 3 (Index Finger) during calibration and control
to ensure a clean, smooth, and quiet performance on camera.

Features:
  1. 3-second countdown to prepare your camera.
  2. Quiet calibration of ONLY the working fingers.
  3. Coordinated finger waves, claw grasps, and gestures.
"""

import time
import sys
from ehand_driver import EHand6Driver, HandID, ControlMode, FingerParams

# List of working motor IDs
WORKING_MOTORS = [1, 2, 4, 5, 6]

def countdown(seconds=3):
    print("\n" + "=" * 50)
    print("  GET YOUR PHONE CAMERA READY FOR THE VIDEO!")
    print("=" * 50)
    for i in range(seconds, 0, -1):
        print(f"  Starting in {i}...")
        time.sleep(1.0)
    print("  ACTION! 🎬")
    print("=" * 50)

def send_working_position(driver, positions, speed=128, torque=204):
    """
    Send target positions for only the working fingers.
    positions: dict mapping motor_id (1,2,4,5,6) to value (0-255)
    """
    fingers = {}
    for mid in WORKING_MOTORS:
        pos = positions.get(mid, 128)  # default to center
        fingers[mid] = FingerParams(position=pos, speed=speed, torque=torque)
        
    data = driver._build_control_frame(
        mode=ControlMode.POSITION, 
        fingers=fingers, 
        motor_ids=WORKING_MOTORS
    )
    driver._send_frame(data)

def main():
    driver = EHand6Driver(channel='can0', hand_id=HandID.RIGHT)
    
    try:
        driver.connect()
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return

    # Warm up status read
    driver.read_status()
    
    # 1. Camera countdown
    countdown(3)

    try:
        # 2. Calibrate ONLY the working motors (avoids index finger stall/hum)
        print("\n[DEMO] Calibrating working fingers (1, 2, 4, 5, 6)...")
        data = driver._build_control_frame(mode=ControlMode.ZEROING, motor_ids=WORKING_MOTORS)
        driver._send_frame(data)
        time.sleep(5.0)  # Wait for calibration to complete

        # 3. Wave Gesture (Finger Ripple)
        print("\n[DEMO] Starting Wave Ripple...")
        ripple_steps = [
            {1: 255, 2: 255, 4: 0, 5: 0, 6: 0},     # Thumb bent, others open
            {1: 255, 2: 255, 4: 255, 5: 0, 6: 0},   # Middle bend
            {1: 255, 2: 255, 4: 255, 5: 255, 6: 0}, # Ring bend
            {1: 255, 2: 255, 4: 255, 5: 255, 6: 255}, # All working bent
            {1: 0, 2: 0, 4: 255, 5: 255, 6: 255},   # Thumb open
            {1: 0, 2: 0, 4: 0, 5: 255, 6: 255},     # Middle open
            {1: 0, 2: 0, 4: 0, 5: 0, 6: 255},       # Ring open
            {1: 0, 2: 0, 4: 0, 5: 0, 6: 0},         # Little open
        ]
        for step in ripple_steps:
            send_working_position(driver, step, speed=160)
            time.sleep(0.6)

        time.sleep(1.0)

        # 4. Claw Grasp (Coordinated Close / Open)
        print("\n[DEMO] Claw Grasp (Full Close and Open)...")
        # Full Close
        send_working_position(driver, {1: 255, 2: 255, 4: 255, 5: 255, 6: 255}, speed=100)
        time.sleep(2.0)
        # Full Open
        send_working_position(driver, {1: 0, 2: 0, 4: 0, 5: 0, 6: 0}, speed=100)
        time.sleep(2.0)

        # 5. Thumbs Up 👍 Gesture
        # Since the index finger is stuck closed, bending the middle, ring, and little fingers 
        # while keeping the thumb fully extended creates a perfect thumbs-up!
        print("\n[DEMO] Thumbs Up 👍...")
        thumbs_up = {
            1: 0,    # Thumb horizontal extended
            2: 0,    # Thumb vertical extended
            4: 255,  # Middle closed
            5: 255,  # Ring closed
            6: 255,  # Little closed
        }
        send_working_position(driver, thumbs_up, speed=140)
        time.sleep(3.0)

        # 6. Victory/Peace Sign ✌️ (Adapted)
        # Bends thumb, ring, and little, extends middle.
        print("\n[DEMO] Adapted Peace Sign...")
        peace_sign = {
            1: 255,
            2: 255,
            4: 0,    # Middle extended
            5: 255,
            6: 255,
        }
        send_working_position(driver, peace_sign, speed=140)
        time.sleep(3.0)

        # 7. Final Return to Standby Open
        print("\n[DEMO] Finalizing: Return to open...")
        send_working_position(driver, {1: 0, 2: 0, 4: 0, 5: 0, 6: 0}, speed=100)
        time.sleep(2.0)

        print("\n[DEMO] Sequence finished successfully!")

    except KeyboardInterrupt:
        print("\n[DEMO] Interrupted by user. Stopping all motors.")
        driver.emergency_stop()
    finally:
        driver.emergency_stop()  # Turn off torque
        driver.disconnect()
        print("\n=== Demo Complete ===")

if __name__ == "__main__":
    main()
