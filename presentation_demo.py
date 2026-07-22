#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════
  HITBOT eHand-6 — LIVE PRESENTATION DEMO
═══════════════════════════════════════════════════════════════════════════

  Press a, b, c, d, e... to perform gestures in order.
  All keys are consecutive on the keyboard for easy control.

  ⚠ Motor 3 (Index Finger) is bypassed due to mechanical defect.

  Usage:
      python3 presentation_demo.py
      python3 presentation_demo.py --skip-cal

═══════════════════════════════════════════════════════════════════════════
"""

import sys
import time
import os
import argparse

try:
    import readchar
except ImportError:
    print("Installing 'readchar'...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "readchar", "-q"])
    import readchar

from ehand_driver import EHand6Driver, HandID, ControlMode, FingerParams


# ═══════════════════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════════════════

WORKING_MOTORS = [1, 2, 4, 5, 6]

THUMB_H = 1
THUMB_V = 2
MIDDLE  = 4
RING    = 5
LITTLE  = 6

# Positions
OPEN    = 0
CLOSED  = 255
HALF    = 128
SLIGHT  = 60
MOSTLY  = 200

# Speeds
SLOW    = 80
NORMAL  = 128
FAST    = 180
SNAP    = 230

# Torque
GENTLE  = 100
FIRM    = 180
STRONG  = 220


# ═══════════════════════════════════════════════════════════════════════════
# Core control
# ═══════════════════════════════════════════════════════════════════════════

def send_pose(driver, positions, speed=NORMAL, torque=FIRM):
    fingers = {}
    for mid in WORKING_MOTORS:
        pos = positions.get(mid, 0)
        fingers[mid] = FingerParams(position=pos, speed=speed, torque=torque)
    data = driver._build_control_frame(
        mode=ControlMode.POSITION, fingers=fingers, motor_ids=WORKING_MOTORS,
    )
    driver._send_frame(data)
    time.sleep(0.02)


def calibrate(driver):
    print("\n  ⚙  Calibrating working fingers (skip index)...")
    data = driver._build_control_frame(mode=ControlMode.ZEROING, motor_ids=WORKING_MOTORS)
    driver._send_frame(data)
    for i in range(5):
        time.sleep(1.0)
        print(f"\r     {'●' * (i+1)}{'○' * (4-i)}", end="", flush=True)
    print("\r     ✓ Calibration done!              ")
    time.sleep(0.5)
    send_pose(driver, {THUMB_H: OPEN, THUMB_V: OPEN, MIDDLE: OPEN, RING: OPEN, LITTLE: OPEN})
    time.sleep(1.0)


# ═══════════════════════════════════════════════════════════════════════════
# Animated sequences
# ═══════════════════════════════════════════════════════════════════════════

def wave_animation(driver):
    print("    🌊 Waving...")
    send_pose(driver, {THUMB_H: OPEN, THUMB_V: OPEN, MIDDLE: OPEN, RING: OPEN, LITTLE: OPEN}, speed=FAST)
    time.sleep(0.5)
    for _ in range(3):
        send_pose(driver, {THUMB_H: OPEN, THUMB_V: OPEN, MIDDLE: OPEN, RING: OPEN, LITTLE: HALF}, speed=SNAP)
        time.sleep(0.15)
        send_pose(driver, {THUMB_H: OPEN, THUMB_V: OPEN, MIDDLE: OPEN, RING: HALF, LITTLE: CLOSED}, speed=SNAP)
        time.sleep(0.15)
        send_pose(driver, {THUMB_H: OPEN, THUMB_V: OPEN, MIDDLE: HALF, RING: CLOSED, LITTLE: CLOSED}, speed=SNAP)
        time.sleep(0.15)
        send_pose(driver, {THUMB_H: HALF, THUMB_V: HALF, MIDDLE: CLOSED, RING: CLOSED, LITTLE: CLOSED}, speed=SNAP)
        time.sleep(0.15)
        send_pose(driver, {THUMB_H: OPEN, THUMB_V: OPEN, MIDDLE: CLOSED, RING: CLOSED, LITTLE: CLOSED}, speed=SNAP)
        time.sleep(0.15)
        send_pose(driver, {THUMB_H: OPEN, THUMB_V: OPEN, MIDDLE: OPEN, RING: CLOSED, LITTLE: CLOSED}, speed=SNAP)
        time.sleep(0.15)
        send_pose(driver, {THUMB_H: OPEN, THUMB_V: OPEN, MIDDLE: OPEN, RING: OPEN, LITTLE: CLOSED}, speed=SNAP)
        time.sleep(0.15)
        send_pose(driver, {THUMB_H: OPEN, THUMB_V: OPEN, MIDDLE: OPEN, RING: OPEN, LITTLE: OPEN}, speed=SNAP)
        time.sleep(0.3)
    print("    ✓ Done!")


def counting_animation(driver):
    print("    🔢 Counting 1 to 5...")
    send_pose(driver, {THUMB_H: CLOSED, THUMB_V: CLOSED, MIDDLE: CLOSED, RING: CLOSED, LITTLE: CLOSED}, speed=FAST)
    time.sleep(0.8)
    print("      1...")
    send_pose(driver, {THUMB_H: CLOSED, THUMB_V: CLOSED, MIDDLE: OPEN, RING: CLOSED, LITTLE: CLOSED}, speed=SNAP)
    time.sleep(1.0)
    print("      2...")
    send_pose(driver, {THUMB_H: CLOSED, THUMB_V: CLOSED, MIDDLE: OPEN, RING: OPEN, LITTLE: CLOSED}, speed=SNAP)
    time.sleep(1.0)
    print("      3...")
    send_pose(driver, {THUMB_H: CLOSED, THUMB_V: CLOSED, MIDDLE: OPEN, RING: OPEN, LITTLE: OPEN}, speed=SNAP)
    time.sleep(1.0)
    print("      4...")
    send_pose(driver, {THUMB_H: OPEN, THUMB_V: CLOSED, MIDDLE: OPEN, RING: OPEN, LITTLE: OPEN}, speed=SNAP)
    time.sleep(1.0)
    print("      5!")
    send_pose(driver, {THUMB_H: OPEN, THUMB_V: OPEN, MIDDLE: OPEN, RING: OPEN, LITTLE: OPEN}, speed=SNAP)
    time.sleep(1.5)
    print("    ✓ Done!")


def grab_release_animation(driver):
    print("    🫳 Grab & Release...")
    send_pose(driver, {THUMB_H: OPEN, THUMB_V: OPEN, MIDDLE: OPEN, RING: OPEN, LITTLE: OPEN}, speed=NORMAL)
    time.sleep(1.0)
    send_pose(driver, {THUMB_H: SLIGHT, THUMB_V: SLIGHT, MIDDLE: SLIGHT, RING: SLIGHT, LITTLE: SLIGHT}, speed=SLOW)
    time.sleep(0.8)
    send_pose(driver, {THUMB_H: MOSTLY, THUMB_V: MOSTLY, MIDDLE: MOSTLY, RING: MOSTLY, LITTLE: MOSTLY}, speed=SLOW)
    time.sleep(0.5)
    send_pose(driver, {THUMB_H: CLOSED, THUMB_V: CLOSED, MIDDLE: CLOSED, RING: CLOSED, LITTLE: CLOSED}, speed=SLOW)
    time.sleep(2.0)
    send_pose(driver, {THUMB_H: HALF, THUMB_V: HALF, MIDDLE: HALF, RING: HALF, LITTLE: HALF}, speed=SLOW)
    time.sleep(0.4)
    send_pose(driver, {THUMB_H: OPEN, THUMB_V: OPEN, MIDDLE: OPEN, RING: OPEN, LITTLE: OPEN}, speed=SLOW)
    time.sleep(1.0)
    print("    ✓ Done!")


def finger_tap_animation(driver):
    print("    🎹 Finger tapping...")
    send_pose(driver, {THUMB_H: SLIGHT, THUMB_V: SLIGHT, MIDDLE: OPEN, RING: OPEN, LITTLE: OPEN}, speed=FAST)
    time.sleep(0.5)
    for _ in range(4):
        send_pose(driver, {THUMB_H: SLIGHT, THUMB_V: SLIGHT, MIDDLE: OPEN, RING: OPEN, LITTLE: HALF}, speed=SNAP)
        time.sleep(0.12)
        send_pose(driver, {THUMB_H: SLIGHT, THUMB_V: SLIGHT, MIDDLE: OPEN, RING: OPEN, LITTLE: OPEN}, speed=SNAP)
        time.sleep(0.08)
        send_pose(driver, {THUMB_H: SLIGHT, THUMB_V: SLIGHT, MIDDLE: OPEN, RING: HALF, LITTLE: OPEN}, speed=SNAP)
        time.sleep(0.12)
        send_pose(driver, {THUMB_H: SLIGHT, THUMB_V: SLIGHT, MIDDLE: OPEN, RING: OPEN, LITTLE: OPEN}, speed=SNAP)
        time.sleep(0.08)
        send_pose(driver, {THUMB_H: SLIGHT, THUMB_V: SLIGHT, MIDDLE: HALF, RING: OPEN, LITTLE: OPEN}, speed=SNAP)
        time.sleep(0.12)
        send_pose(driver, {THUMB_H: SLIGHT, THUMB_V: SLIGHT, MIDDLE: OPEN, RING: OPEN, LITTLE: OPEN}, speed=SNAP)
        time.sleep(0.15)
    print("    ✓ Done!")


def handshake_animation(driver):
    print("    🤝 Handshake...")
    send_pose(driver, {THUMB_H: OPEN, THUMB_V: OPEN, MIDDLE: OPEN, RING: OPEN, LITTLE: OPEN}, speed=NORMAL)
    time.sleep(1.0)
    send_pose(driver, {THUMB_H: HALF, THUMB_V: HALF, MIDDLE: MOSTLY, RING: MOSTLY, LITTLE: MOSTLY}, speed=NORMAL)
    time.sleep(0.5)
    for _ in range(3):
        send_pose(driver, {THUMB_H: SLIGHT, THUMB_V: SLIGHT, MIDDLE: HALF, RING: HALF, LITTLE: HALF}, speed=FAST)
        time.sleep(0.3)
        send_pose(driver, {THUMB_H: HALF, THUMB_V: HALF, MIDDLE: MOSTLY, RING: MOSTLY, LITTLE: MOSTLY}, speed=FAST)
        time.sleep(0.3)
    time.sleep(0.3)
    send_pose(driver, {THUMB_H: OPEN, THUMB_V: OPEN, MIDDLE: OPEN, RING: OPEN, LITTLE: OPEN}, speed=SLOW)
    time.sleep(1.0)
    print("    ✓ Done!")


# ═══════════════════════════════════════════════════════════════════════════
# All actions in order: a, b, c, d, e, f, g, h, i, j, k, l, m, n, o, p
# ═══════════════════════════════════════════════════════════════════════════

ACTIONS = [
    # (key, emoji+name, description, type, data)
    # type: "pose" for instant, "anim" for animated sequence

    ("a", "🖐  OPEN HAND",         "All fingers fully extended",
     "pose", {THUMB_H: OPEN, THUMB_V: OPEN, MIDDLE: OPEN, RING: OPEN, LITTLE: OPEN},
     NORMAL, FIRM),

    ("b", "✊  FIST",              "All fingers closed tight",
     "pose", {THUMB_H: CLOSED, THUMB_V: CLOSED, MIDDLE: CLOSED, RING: CLOSED, LITTLE: CLOSED},
     NORMAL, STRONG),

    ("c", "👍  THUMBS UP",         "Thumb up, others closed",
     "pose", {THUMB_H: OPEN, THUMB_V: OPEN, MIDDLE: CLOSED, RING: CLOSED, LITTLE: CLOSED},
     FAST, FIRM),

    ("d", "👎  THUMBS DOWN",       "Everything curled in",
     "pose", {THUMB_H: CLOSED, THUMB_V: CLOSED, MIDDLE: CLOSED, RING: CLOSED, LITTLE: CLOSED},
     FAST, FIRM),

    ("e", "🤏  PINCH GRIP",        "Thumb + middle precision pinch",
     "pose", {THUMB_H: MOSTLY, THUMB_V: MOSTLY, MIDDLE: MOSTLY, RING: SLIGHT, LITTLE: SLIGHT},
     SLOW, GENTLE),

    ("f", "🤘  ROCK ON",           "Thumb + little up, others closed",
     "pose", {THUMB_H: OPEN, THUMB_V: OPEN, MIDDLE: CLOSED, RING: CLOSED, LITTLE: OPEN},
     FAST, FIRM),

    ("g", "🤙  CALL ME / SHAKA",   "Thumb + pinky extended",
     "pose", {THUMB_H: OPEN, THUMB_V: OPEN, MIDDLE: CLOSED, RING: CLOSED, LITTLE: OPEN},
     FAST, FIRM),

    ("h", "3️⃣   THREE",             "Middle + Ring + Little up",
     "pose", {THUMB_H: CLOSED, THUMB_V: CLOSED, MIDDLE: OPEN, RING: OPEN, LITTLE: OPEN},
     FAST, FIRM),

    ("i", "👆  POINT",             "Middle finger points forward",
     "pose", {THUMB_H: CLOSED, THUMB_V: CLOSED, MIDDLE: OPEN, RING: CLOSED, LITTLE: CLOSED},
     FAST, FIRM),

    ("j", "👌  OK SIGN",           "Thumb + middle circle, others open",
     "pose", {THUMB_H: MOSTLY, THUMB_V: MOSTLY, MIDDLE: MOSTLY, RING: OPEN, LITTLE: OPEN},
     NORMAL, FIRM),

    ("k", "😌  NATURAL REST",      "Relaxed, slightly curled",
     "pose", {THUMB_H: SLIGHT, THUMB_V: SLIGHT, MIDDLE: SLIGHT, RING: SLIGHT, LITTLE: SLIGHT},
     SLOW, GENTLE),

    ("l", "🌊  WAVE",              "Animated waving hello",
     "anim", None, None, None),

    ("m", "🔢  COUNT 1-5",         "Counts with fingers one by one",
     "anim", None, None, None),

    ("n", "🫳  GRAB & RELEASE",    "Pick up & release invisible object",
     "anim", None, None, None),

    ("o", "🎹  FINGER TAP",        "Impatient drumming on table",
     "anim", None, None, None),

    ("p", "🤝  HANDSHAKE",         "Grip, pump, and release",
     "anim", None, None, None),
]

ANIM_FUNCS = {
    "l": wave_animation,
    "m": counting_animation,
    "n": grab_release_animation,
    "o": finger_tap_animation,
    "p": handshake_animation,
}


# ═══════════════════════════════════════════════════════════════════════════
# Menu
# ═══════════════════════════════════════════════════════════════════════════

def clear_screen():
    os.system('clear' if os.name != 'nt' else 'cls')


def print_menu():
    print()
    print("═" * 60)
    print("  🤖  HITBOT eHand-6 — LIVE DEMO")
    print("═" * 60)
    print()
    print("  ┌────────────────────────────────────────────────────┐")
    print("  │  INSTANT GESTURES                                 │")
    print("  ├────────────────────────────────────────────────────┤")

    for key, name, desc, typ, *_ in ACTIONS:
        if typ == "pose":
            print(f"  │  [ {key} ]  {name:38s}  │")

    print("  ├────────────────────────────────────────────────────┤")
    print("  │  ANIMATED SEQUENCES                               │")
    print("  ├────────────────────────────────────────────────────┤")

    for key, name, desc, typ, *_ in ACTIONS:
        if typ == "anim":
            print(f"  │  [ {key} ]  {name:38s}  │")

    print("  ├────────────────────────────────────────────────────┤")
    print("  │  CONTROLS                                         │")
    print("  ├────────────────────────────────────────────────────┤")
    print("  │  [ z ]  ⚙  RE-CALIBRATE                           │")
    print("  │  [SPC]  🛑  EMERGENCY STOP                        │")
    print("  │  [ r ]  📋  REFRESH MENU                           │")
    print("  │  [ q ]  🚪  QUIT                                   │")
    print("  └────────────────────────────────────────────────────┘")
    print()
    print("  ⚠  Index finger skipped (mechanical defect)")
    print("  📡 Press any key a–p to go!")
    print()


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="eHand-6 Live Demo")
    parser.add_argument("--channel", default="can0")
    parser.add_argument("--hand", choices=["left", "right"], default="right")
    parser.add_argument("--skip-cal", action="store_true", help="Skip calibration")
    args = parser.parse_args()

    hand_id = HandID.RIGHT if args.hand == "right" else HandID.LEFT

    driver = EHand6Driver(channel=args.channel, hand_id=hand_id)

    try:
        driver.connect()
    except Exception as e:
        print(f"\n  ✗ Connection failed: {e}")
        print("    → Run: sudo ./setup_can.sh")
        sys.exit(1)

    status = driver.read_status()
    if status is None:
        print("\n  ✗ No response from hand!")
        driver.disconnect()
        sys.exit(1)

    print(f"  ✓ Hand connected — {status.machine_state_name}")

    if not args.skip_cal:
        calibrate(driver)
    else:
        print("  ⏭  Skipping calibration")

    # Build lookup dicts for fast key handling
    pose_map = {}
    for key, name, desc, typ, positions, speed, torque in ACTIONS:
        if typ == "pose":
            pose_map[key] = (name, desc, positions, speed, torque)

    clear_screen()
    print_menu()

    try:
        while True:
            key = readchar.readkey()

            if key in (readchar.key.ESC, 'q', 'Q'):
                print("\n  🚪 Exiting...")
                break

            if key == ' ':
                driver.emergency_stop()
                print("\n  🛑 EMERGENCY STOP!")
                print("     Press [z] to re-calibrate, or [q] to quit.")
                continue

            if key in ('r', 'R'):
                clear_screen()
                print_menu()
                continue

            if key in ('z', 'Z'):
                calibrate(driver)
                print("  📡 Ready!")
                continue

            k = key.lower()

            if k in pose_map:
                name, desc, positions, speed, torque = pose_map[k]
                print(f"\n  ▶  {name}  —  {desc}")
                send_pose(driver, positions, speed=speed, torque=torque)
                continue

            if k in ANIM_FUNCS:
                # Find display name
                for ak, aname, adesc, *_ in ACTIONS:
                    if ak == k:
                        print(f"\n  ▶  {aname}  —  {adesc}")
                        break
                ANIM_FUNCS[k](driver)
                continue

    except KeyboardInterrupt:
        print("\n\n  ⚠ Interrupted!")
    finally:
        print("  Stopping motors...")
        try:
            driver.emergency_stop()
        except Exception:
            pass
        driver.disconnect()
        print("\n  ✓ Done! Good luck with the presentation! 🎉\n")


if __name__ == "__main__":
    main()
