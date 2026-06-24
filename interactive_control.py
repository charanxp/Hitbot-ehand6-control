#!/usr/bin/env python3
"""
HITBOT eHand-6 Interactive Controller
=======================================
Real-time interactive CLI for controlling the eHand-6.
Provides keyboard shortcuts for gestures and individual finger control.

Usage:
  python3 interactive_control.py [--hand right|left] [--channel can0]

Controls:
  Number keys 1-6: Select finger to control
  o: Open hand
  c: Close hand
  z: Zero/calibrate hand
  s: Read status
  r: Reset to center position
  +/-: Increase/decrease selected finger position
  SPACE: Emergency stop
  q: Quit
"""

import sys
import time
import argparse
import threading

from ehand_driver import (
    EHand6Driver, HandID, FingerParams, ControlMode, MOTOR_NAMES
)


class InteractiveController:
    """Interactive CLI controller for eHand-6."""

    def __init__(self, driver: EHand6Driver):
        self.driver = driver
        self.selected_motor = 0  # 0 = all, 1-6 = individual
        self.speed = 0x80        # Default 50%
        self.torque = 0xCC       # Default 80%

        # Current target positions for all 6 motors
        self.positions = [0x80] * 6  # All at center

        # Status polling
        self.running = True
        self.last_status = None

    def print_help(self):
        """Print the control help menu."""
        print("\n" + "=" * 60)
        print("  eHand-6 Interactive Controller")
        print("=" * 60)
        print()
        print("  FINGER SELECTION:")
        print("    0       Select ALL fingers")
        print("    1       Thumb Horizontal")
        print("    2       Thumb Vertical")
        print("    3       Index Finger")
        print("    4       Middle Finger")
        print("    5       Ring Finger")
        print("    6       Little Finger")
        print()
        print("  GESTURES:")
        print("    o       Open hand (all fingers)")
        print("    c       Close hand (all fingers)")
        print("    r       Reset to center (50%)")
        print("    z       Zero/calibrate")
        print()
        print("  POSITION CONTROL:")
        print("    +/=     Increase position by 10%")
        print("    -       Decrease position by 10%")
        print("    f       Set to fully closed (100%)")
        print("    g       Set to fully open (0%)")
        print()
        print("  SPEED/TORQUE:")
        print("    [       Decrease speed by 10%")
        print("    ]       Increase speed by 10%")
        print("    ;       Decrease torque by 10%")
        print("    '       Increase torque by 10%")
        print()
        print("  OTHER:")
        print("    s       Read and display status")
        print("    p       Save current position as point 1")
        print("    x       Execute saved point 1")
        print("    SPACE   EMERGENCY STOP")
        print("    h       Show this help")
        print("    q       Quit")
        print("=" * 60)

    def print_state(self):
        """Print current controller state."""
        sel = "ALL" if self.selected_motor == 0 else MOTOR_NAMES.get(self.selected_motor, "?")
        print(f"\n  Selected: {sel} | Speed: {self.speed/2.55:.0f}% | Torque: {self.torque/2.55:.0f}%")
        print("  Positions: ", end="")
        for i in range(6):
            name_short = ["ThH", "ThV", "Idx", "Mid", "Rng", "Lit"][i]
            marker = "►" if (self.selected_motor == i + 1) else " "
            print(f"{marker}{name_short}:{self.positions[i]/2.55:4.0f}%", end="  ")
        print()

    def send_positions(self):
        """Send current position state to the hand."""
        fingers = {}
        for i in range(6):
            fingers[i + 1] = FingerParams(
                position=self.positions[i],
                speed=self.speed,
                torque=self.torque,
            )

        if self.selected_motor == 0:
            # All motors
            data = self.driver._build_control_frame(
                ControlMode.POSITION, fingers
            )
        else:
            # Single motor
            motor_fingers = {
                self.selected_motor: fingers[self.selected_motor]
            }
            data = self.driver._build_control_frame(
                ControlMode.POSITION,
                motor_fingers,
                motor_ids=[self.selected_motor],
            )

        self.driver._send_frame(data)

        # Try to read response
        msg = self.driver._receive_frame(timeout=0.2)
        if msg:
            self.last_status = self.driver._parse_status(msg)

    def adjust_position(self, delta: int):
        """Adjust position of selected motor(s)."""
        if self.selected_motor == 0:
            for i in range(6):
                self.positions[i] = max(0, min(255, self.positions[i] + delta))
        else:
            idx = self.selected_motor - 1
            self.positions[idx] = max(0, min(255, self.positions[idx] + delta))

        self.send_positions()
        self.print_state()

    def run(self):
        """Main interactive loop."""
        self.print_help()
        self.print_state()

        while self.running:
            try:
                cmd = input("\n  cmd> ").strip().lower()
            except (KeyboardInterrupt, EOFError):
                cmd = 'q'

            if not cmd:
                continue

            for ch in cmd:
                self._handle_key(ch)

    def _handle_key(self, key: str):
        """Handle a single keypress."""
        if key == 'q':
            print("\n  Quitting... opening hand first.")
            self.driver.open_hand(speed=0x80, torque=0xCC)
            time.sleep(1)
            self.running = False

        elif key == ' ':
            self.driver.emergency_stop()

        elif key == 'h':
            self.print_help()

        elif key in '0123456':
            self.selected_motor = int(key)
            sel = "ALL" if self.selected_motor == 0 else MOTOR_NAMES.get(self.selected_motor, "?")
            print(f"  → Selected: {sel}")
            self.print_state()

        elif key == 'o':
            print("  → Opening hand...")
            for i in range(6):
                self.positions[i] = 0x00
            self.driver.open_hand(speed=self.speed, torque=self.torque)
            time.sleep(0.5)
            self.print_state()

        elif key == 'c':
            print("  → Closing hand...")
            for i in range(6):
                self.positions[i] = 0xFF
            self.driver.close_hand(speed=self.speed, torque=self.torque)
            time.sleep(0.5)
            self.print_state()

        elif key == 'z':
            print("  → Zeroing hand (calibrating)...")
            self.driver.zero_hand()
            for i in range(6):
                self.positions[i] = 0x00
            time.sleep(3)
            print("  → Zero complete")
            self.print_state()

        elif key == 'r':
            print("  → Resetting to center (50%)...")
            for i in range(6):
                self.positions[i] = 0x80
            self.send_positions()
            self.print_state()

        elif key in ('+', '='):
            self.adjust_position(26)  # +~10%

        elif key == '-':
            self.adjust_position(-26)  # -~10%

        elif key == 'f':
            print("  → Fully closed (100%)")
            if self.selected_motor == 0:
                for i in range(6):
                    self.positions[i] = 0xFF
            else:
                self.positions[self.selected_motor - 1] = 0xFF
            self.send_positions()
            self.print_state()

        elif key == 'g':
            print("  → Fully open (0%)")
            if self.selected_motor == 0:
                for i in range(6):
                    self.positions[i] = 0x00
            else:
                self.positions[self.selected_motor - 1] = 0x00
            self.send_positions()
            self.print_state()

        elif key == 's':
            print("  → Reading status...")
            status = self.driver.read_status()
            if status:
                self.driver.print_status(status)
                self.last_status = status
            else:
                print("  ✗ No response")

        elif key == 'p':
            print("  → Saving current positions as point 1...")
            self.driver.save_point(1)

        elif key == 'x':
            print("  → Executing saved point 1...")
            self.driver.execute_point(1)

        elif key == '[':
            self.speed = max(0, self.speed - 26)
            print(f"  → Speed: {self.speed/2.55:.0f}%")

        elif key == ']':
            self.speed = min(255, self.speed + 26)
            print(f"  → Speed: {self.speed/2.55:.0f}%")

        elif key == ';':
            self.torque = max(0, self.torque - 26)
            print(f"  → Torque: {self.torque/2.55:.0f}%")

        elif key == "'":
            self.torque = min(255, self.torque + 26)
            print(f"  → Torque: {self.torque/2.55:.0f}%")

        else:
            pass  # Ignore unknown keys


def main():
    parser = argparse.ArgumentParser(
        description="HITBOT eHand-6 Interactive Controller"
    )
    parser.add_argument(
        '--hand', choices=['right', 'left'], default='right',
        help='Which hand (default: right)'
    )
    parser.add_argument(
        '--channel', default='can0',
        help='CAN interface (default: can0)'
    )
    args = parser.parse_args()

    hand_id = HandID.RIGHT if args.hand == 'right' else HandID.LEFT

    with EHand6Driver(channel=args.channel, hand_id=hand_id) as driver:
        controller = InteractiveController(driver)
        try:
            controller.run()
        except KeyboardInterrupt:
            print("\n  ⚠ Interrupted — sending emergency stop")
            driver.emergency_stop()


if __name__ == "__main__":
    main()
