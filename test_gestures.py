#!/usr/bin/env python3
"""
HITBOT eHand-6 Safe Gesture Test Sequence
==========================================
Runs through a series of safe test gestures, one at a time.
Each step waits for user confirmation before proceeding.

Prerequisites:
  1. test_connection.py passed
  2. CAN FD interface is up
  3. Hand is powered and responding

Usage:
  python3 test_gestures.py [--hand right|left] [--channel can0] [--auto]
"""

import sys
import time
import argparse

from ehand_driver import EHand6Driver, HandID, FingerParams


def wait_for_user(prompt: str = "Press ENTER to continue (or 'q' to quit)") -> bool:
    """Wait for user input. Returns False if user wants to quit."""
    try:
        response = input(f"\n  >>> {prompt}: ").strip().lower()
        return response != 'q'
    except (KeyboardInterrupt, EOFError):
        return False


def run_gesture_sequence(driver: EHand6Driver, auto_mode: bool = False):
    """Run the complete safe test sequence."""

    def step(name: str, description: str) -> bool:
        print(f"\n{'─' * 60}")
        print(f"  STEP: {name}")
        print(f"  {description}")
        print(f"{'─' * 60}")
        if not auto_mode:
            if not wait_for_user():
                return False
        else:
            time.sleep(0.5)
        return True

    # ── Step 1: Read Status ──
    if not step("READ STATUS", "Read current hand state (non-destructive)"):
        return

    status = driver.read_status()
    driver.print_status(status)
    if status is None:
        print("  ✗ Cannot proceed — hand not responding")
        return

    # ── Step 2: Zero/Calibrate ──
    if not step(
        "ZERO ALL FINGERS",
        "Calibrate all motors to their zero reference.\n"
        "  The hand will move! Keep clear of moving parts."
    ):
        return

    print("  Sending zeroing command...")
    status = driver.zero_hand()
    if status:
        driver.print_status(status)
    print("  Waiting 5 seconds for zeroing to complete...")
    time.sleep(5)

    # Read status after zeroing
    status = driver.read_status()
    driver.print_status(status)

    # ── Step 3: Open Hand ──
    if not step(
        "OPEN HAND",
        "Open all fingers using FINGER_OPEN mode.\n"
        "  Speed: 50%, Torque: 80%"
    ):
        return

    print("  Sending open command...")
    status = driver.open_hand(speed=0x80, torque=0xCC)
    if status:
        driver.print_status(status)
    time.sleep(2)

    # ── Step 4: Close Hand ──
    if not step(
        "CLOSE HAND",
        "Close all fingers using FINGER_CLOSE mode.\n"
        "  Speed: 50%, Torque: 80%\n"
        "  ⚠ Make sure nothing is between the fingers!"
    ):
        return

    print("  Sending close command...")
    status = driver.close_hand(speed=0x80, torque=0xCC)
    if status:
        driver.print_status(status)
    time.sleep(2)

    # ── Step 5: Center Position ──
    if not step(
        "CENTER ALL FINGERS",
        "Move all fingers to 50% position (center).\n"
        "  Position: 128/255 (50%), Speed: 50%, Torque: 80%"
    ):
        return

    print("  Sending position command (center)...")
    status = driver.set_all_fingers(position=0x80, speed=0x80, torque=0xCC)
    if status:
        driver.print_status(status)
    time.sleep(2)

    # ── Step 6: Individual Finger Test ──
    finger_tests = [
        (1, "THUMB HORIZONTAL", "Rotate thumb left/right"),
        (2, "THUMB VERTICAL",   "Extend/retract thumb"),
        (3, "INDEX FINGER",     "Close and open index finger"),
        (4, "MIDDLE FINGER",    "Close and open middle finger"),
        (5, "RING FINGER",      "Close and open ring finger"),
        (6, "LITTLE FINGER",    "Close and open little finger"),
    ]

    for motor_id, name, desc in finger_tests:
        if not step(
            f"TEST {name} (Motor {motor_id})",
            f"{desc}\n"
            f"  Will close to 80%, then open to 20%"
        ):
            return

        # Close this finger
        print(f"  Closing {name} to 80%...")
        driver.set_finger(motor_id, position=0xCC, speed=0x80, torque=0xCC)
        time.sleep(1.5)

        # Open this finger
        print(f"  Opening {name} to 20%...")
        driver.set_finger(motor_id, position=0x33, speed=0x80, torque=0xCC)
        time.sleep(1.5)

        # Return to center
        print(f"  Returning {name} to center...")
        driver.set_finger(motor_id, position=0x80, speed=0x80, torque=0xCC)
        time.sleep(0.5)

    # ── Step 7: Predefined Gestures ──
    gestures = [
        (
            "PEACE SIGN ✌️",
            "Index and middle fingers extended, others closed",
            {
                1: FingerParams(0x00, 0x80, 0xCC),  # Thumb horiz open
                2: FingerParams(0x00, 0x80, 0xCC),  # Thumb vert open
                3: FingerParams(0x00, 0x80, 0xCC),  # Index open
                4: FingerParams(0x00, 0x80, 0xCC),  # Middle open
                5: FingerParams(0xFF, 0x80, 0xCC),  # Ring closed
                6: FingerParams(0xFF, 0x80, 0xCC),  # Little closed
            }
        ),
        (
            "THUMBS UP 👍",
            "Thumb extended, all other fingers closed",
            {
                1: FingerParams(0x00, 0x80, 0xCC),  # Thumb horiz
                2: FingerParams(0x00, 0x80, 0xCC),  # Thumb vert extended
                3: FingerParams(0xFF, 0x80, 0xCC),  # Index closed
                4: FingerParams(0xFF, 0x80, 0xCC),  # Middle closed
                5: FingerParams(0xFF, 0x80, 0xCC),  # Ring closed
                6: FingerParams(0xFF, 0x80, 0xCC),  # Little closed
            }
        ),
        (
            "PINCH 🤏",
            "Thumb and index finger partially closed, others open",
            {
                1: FingerParams(0xCC, 0x80, 0x80),  # Thumb horiz
                2: FingerParams(0xCC, 0x80, 0x80),  # Thumb vert
                3: FingerParams(0xCC, 0x80, 0x80),  # Index
                4: FingerParams(0x00, 0x80, 0xCC),  # Middle open
                5: FingerParams(0x00, 0x80, 0xCC),  # Ring open
                6: FingerParams(0x00, 0x80, 0xCC),  # Little open
            }
        ),
        (
            "FIST ✊",
            "All fingers fully closed",
            {
                1: FingerParams(0xFF, 0x80, 0xCC),
                2: FingerParams(0xFF, 0x80, 0xCC),
                3: FingerParams(0xFF, 0x80, 0xCC),
                4: FingerParams(0xFF, 0x80, 0xCC),
                5: FingerParams(0xFF, 0x80, 0xCC),
                6: FingerParams(0xFF, 0x80, 0xCC),
            }
        ),
    ]

    for gesture_name, gesture_desc, fingers in gestures:
        if not step(
            f"GESTURE: {gesture_name}",
            gesture_desc
        ):
            return

        from ehand_driver import ControlMode
        data = driver._build_control_frame(ControlMode.POSITION, fingers)
        driver._send_frame(data)
        msg = driver._receive_frame()
        if msg:
            status = driver._parse_status(msg)
            driver.print_status(status)
        time.sleep(2)

    # ── Final: Open hand and read final status ──
    if not step("FINAL: OPEN HAND", "Return hand to open position"):
        return

    driver.open_hand(speed=0x80, torque=0xCC)
    time.sleep(2)

    print("\n  Reading final status...")
    status = driver.read_status()
    driver.print_status(status)

    print("\n" + "=" * 60)
    print("  ✓ GESTURE TEST SEQUENCE COMPLETE")
    print("  All tests passed. The hand is responding correctly.")
    print("  You can now run: python3 interactive_control.py")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="HITBOT eHand-6 Safe Gesture Test Sequence"
    )
    parser.add_argument(
        '--hand', choices=['right', 'left'], default='right',
        help='Which hand to test (default: right)'
    )
    parser.add_argument(
        '--channel', default='can0',
        help='CAN interface name (default: can0)'
    )
    parser.add_argument(
        '--auto', action='store_true',
        help='Run automatically without waiting for user input (USE WITH CAUTION)'
    )
    args = parser.parse_args()

    hand_id = HandID.RIGHT if args.hand == 'right' else HandID.LEFT

    print("=" * 60)
    print("  HITBOT eHand-6 Safe Gesture Test")
    print("=" * 60)
    print(f"  Hand:    {args.hand.upper()} (ID: 0x{hand_id:02X})")
    print(f"  Channel: {args.channel}")
    print(f"  Mode:    {'AUTO (⚠ no confirmation!)' if args.auto else 'INTERACTIVE'}")
    print()
    print("  ⚠ The hand WILL MOVE during this test!")
    print("  ⚠ Keep fingers and objects clear of the hand!")

    if args.auto:
        print("\n  ⚠ AUTO MODE: Starting in 3 seconds...")
        time.sleep(3)

    with EHand6Driver(channel=args.channel, hand_id=hand_id) as driver:
        try:
            run_gesture_sequence(driver, auto_mode=args.auto)
        except KeyboardInterrupt:
            print("\n\n  ⚠ Interrupted! Sending emergency stop...")
            driver.emergency_stop()
            print("  Emergency stop sent.")


if __name__ == "__main__":
    main()
