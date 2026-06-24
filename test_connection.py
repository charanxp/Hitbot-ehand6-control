#!/usr/bin/env python3
"""
HITBOT eHand-6 Connection Test
===============================
Verifies CAN FD connectivity and reads the hand status.
Run this FIRST to confirm everything is wired and configured correctly.

Prerequisites:
  1. CAN FD interface is up:
     sudo ip link set can0 up type can bitrate 1000000 sample-point 0.800 \
         dbitrate 5000000 dsample-point 0.750 fd on
  2. Hand is powered with 24V
  3. CAN wiring is correct (Black=CAN_H, White=CAN_L per manual)

Usage:
  python3 test_connection.py [--hand right|left] [--channel can0]
"""

import sys
import time
import argparse
import subprocess

from ehand_driver import EHand6Driver, HandID


def check_can_interface(channel: str) -> bool:
    """Check if the CAN interface exists and is UP."""
    print(f"\n[CHECK] CAN interface '{channel}'...")

    try:
        result = subprocess.run(
            ['ip', '-details', 'link', 'show', channel],
            capture_output=True, text=True, timeout=5
        )
        output = result.stdout

        if result.returncode != 0:
            print(f"  ✗ Interface '{channel}' not found!")
            print(f"  → Run: sudo ip link set {channel} up type can "
                  "bitrate 1000000 dbitrate 5000000 fd on")
            return False

        # Check state
        if 'state UP' in output or 'UP' in output.split('\n')[0]:
            print(f"  ✓ Interface is UP")
        else:
            print(f"  ✗ Interface exists but is DOWN")
            print(f"  → Run: sudo ip link set {channel} up type can "
                  "bitrate 1000000 dbitrate 5000000 fd on")
            return False

        # Check CAN FD
        if 'fd on' in output or 'fd-non-iso on' in output:
            print(f"  ✓ CAN FD is enabled")
        else:
            print(f"  ⚠ CAN FD may not be enabled — check 'fd on' in output")
            print(f"    Output: {output[:200]}")

        # Check bitrate
        if 'bitrate 1000000' in output:
            print(f"  ✓ Arbitration bitrate: 1 Mbps")
        else:
            print(f"  ⚠ Could not verify arbitration bitrate")

        if 'dbitrate 5000000' in output:
            print(f"  ✓ Data bitrate: 5 Mbps")
        else:
            print(f"  ⚠ Could not verify data bitrate (may need firmware upgrade)")

        return True

    except FileNotFoundError:
        print(f"  ✗ 'ip' command not found. Install iproute2: sudo apt install iproute2")
        return False
    except subprocess.TimeoutExpired:
        print(f"  ✗ Timeout checking interface")
        return False


def check_can_errors(channel: str) -> None:
    """Display CAN bus error statistics."""
    print(f"\n[CHECK] CAN bus error statistics...")
    try:
        result = subprocess.run(
            ['ip', '-s', 'link', 'show', channel],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if 'errors' in line.lower() or 'dropped' in line.lower():
                    print(f"  {line.strip()}")
    except Exception:
        pass


def test_read_status(driver: EHand6Driver) -> bool:
    """Send read status command and check for response."""
    print(f"\n[TEST] Sending read-status command to hand 0x{driver.hand_id:02X}...")

    status = driver.read_status()

    if status is None:
        print("  ✗ No response received!")
        print()
        print("  Possible causes:")
        print("  1. Hand not powered (check 24V supply)")
        print("  2. Wrong CAN ID (right=0x11, left=0x12)")
        print("  3. CAN wiring reversed (swap CAN_H and CAN_L)")
        print("  4. Missing GND connection between CANable and PSU")
        print("  5. Wrong bitrate (must be 1 Mbps arb + 5 Mbps data)")
        print("  6. CAN FD not supported by firmware (need to flash)")
        print("  7. Termination missing (enable TERM jumper on CANable)")
        return False

    print("  ✓ Response received!")
    driver.print_status(status)

    # Check for faults
    has_fault = False
    for name, fs in status.fingers.items():
        if fs.fault != 0:
            has_fault = True
            print(f"  ⚠ {name} has fault: {fs.fault_name}")

    if not has_fault:
        print("  ✓ No faults detected")

    return True


def main():
    parser = argparse.ArgumentParser(
        description="HITBOT eHand-6 Connection Test",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 test_connection.py                    # Default: right hand on can0
  python3 test_connection.py --hand left        # Test left hand
  python3 test_connection.py --channel can1     # Use different interface
        """
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
        '--retries', type=int, default=3,
        help='Number of read attempts (default: 3)'
    )
    args = parser.parse_args()

    hand_id = HandID.RIGHT if args.hand == 'right' else HandID.LEFT

    print("=" * 60)
    print("  HITBOT eHand-6 Connection Test")
    print("=" * 60)
    print(f"  Hand:    {args.hand.upper()} (ID: 0x{hand_id:02X})")
    print(f"  Channel: {args.channel}")
    print(f"  Retries: {args.retries}")

    # Step 1: Check interface
    if not check_can_interface(args.channel):
        print("\n✗ FAILED: CAN interface not ready")
        sys.exit(1)

    # Step 2: Connect and read status
    driver = EHand6Driver(
        channel=args.channel,
        hand_id=hand_id,
        timeout=1.0,
    )

    try:
        driver.connect()
    except Exception as e:
        print(f"\n✗ FAILED: Could not open CAN bus: {e}")
        print("  → Check if interface is up and no other program is using it")
        sys.exit(1)

    # Step 3: Try reading status
    success = False
    for attempt in range(1, args.retries + 1):
        print(f"\n--- Attempt {attempt}/{args.retries} ---")
        if test_read_status(driver):
            success = True
            break
        else:
            if attempt < args.retries:
                print(f"  Retrying in 1 second...")
                time.sleep(1.0)

    # Step 4: Show error stats
    check_can_errors(args.channel)

    # Cleanup
    driver.disconnect()

    # Final result
    print()
    if success:
        print("=" * 60)
        print("  ✓ CONNECTION TEST PASSED")
        print("  The hand is responding on the CAN FD bus.")
        print("  You can now run: python3 test_gestures.py")
        print("=" * 60)
    else:
        print("=" * 60)
        print("  ✗ CONNECTION TEST FAILED")
        print("  See troubleshooting above.")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
