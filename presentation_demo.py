#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════
  HITBOT eHand-6 — LIVE PRESENTATION DEMO (6-FINGER & 5-FINGER COMPATIBLE)
═══════════════════════════════════════════════════════════════════════════

  Press a, b, c, d, e... to perform gestures in order.
  All keys are consecutive on the keyboard for easy control.

  Supports:
    - Auto-detection of Hand ID (tries Left 0x12 first, then Right 0x11)
    - Full 6-finger mode (healthy hand)
    - 5-finger mode (bypasses index finger if --skip-index is set)

  Usage:
      python3 presentation_demo.py
      python3 presentation_demo.py --skip-index
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
# Finger & Position Configuration
# ═══════════════════════════════════════════════════════════════════════════

THUMB_H = 1
THUMB_V = 2
INDEX   = 3
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
# Global working parameters (determined at startup)
# ═══════════════════════════════════════════════════════════════════════════
WORKING_MOTORS = [1, 2, 3, 4, 5, 6]
SKIP_INDEX_MODE = False


# ═══════════════════════════════════════════════════════════════════════════
# Core control
# ═══════════════════════════════════════════════════════════════════════════

def send_pose(driver, positions, speed=NORMAL, torque=FIRM):
    fingers = {}
    for mid in WORKING_MOTORS:
        # If in skip-index mode, we ignore requests for INDEX
        if mid == INDEX and SKIP_INDEX_MODE:
            continue
        pos = positions.get(mid, 0)
        fingers[mid] = FingerParams(position=pos, speed=speed, torque=torque)
    data = driver._build_control_frame(
        mode=ControlMode.POSITION, fingers=fingers, motor_ids=WORKING_MOTORS,
    )
    driver._send_frame(data)
    time.sleep(0.02)


def calibrate(driver):
    print(f"\n  ⚙  Calibrating fingers (motors: {WORKING_MOTORS})...")
    data = driver._build_control_frame(mode=ControlMode.ZEROING, motor_ids=WORKING_MOTORS)
    driver._send_frame(data)
    for i in range(5):
        time.sleep(1.0)
        print(f"\r     {'●' * (i+1)}{'○' * (4-i)}", end="", flush=True)
    print("\r     ✓ Calibration done!              ")
    time.sleep(0.5)
    send_pose(driver, {THUMB_H: OPEN, THUMB_V: OPEN, INDEX: OPEN, MIDDLE: OPEN, RING: OPEN, LITTLE: OPEN})
    time.sleep(1.0)


# ═══════════════════════════════════════════════════════════════════════════
# Animated sequences
# ═══════════════════════════════════════════════════════════════════════════

def wave_animation(driver):
    print("    🌊 Waving...")
    send_pose(driver, {THUMB_H: OPEN, THUMB_V: OPEN, INDEX: OPEN, MIDDLE: OPEN, RING: OPEN, LITTLE: OPEN}, speed=FAST)
    time.sleep(0.5)
    
    for _ in range(3):
        # Wave down
        send_pose(driver, {THUMB_H: OPEN, THUMB_V: OPEN, INDEX: OPEN, MIDDLE: OPEN, RING: OPEN, LITTLE: HALF}, speed=SNAP)
        time.sleep(0.12)
        send_pose(driver, {THUMB_H: OPEN, THUMB_V: OPEN, INDEX: OPEN, MIDDLE: OPEN, RING: HALF, LITTLE: CLOSED}, speed=SNAP)
        time.sleep(0.12)
        send_pose(driver, {THUMB_H: OPEN, THUMB_V: OPEN, INDEX: OPEN, MIDDLE: HALF, RING: CLOSED, LITTLE: CLOSED}, speed=SNAP)
        time.sleep(0.12)
        if not SKIP_INDEX_MODE:
            send_pose(driver, {THUMB_H: OPEN, THUMB_V: OPEN, INDEX: HALF, MIDDLE: CLOSED, RING: CLOSED, LITTLE: CLOSED}, speed=SNAP)
            time.sleep(0.12)
            send_pose(driver, {THUMB_H: HALF, THUMB_V: HALF, INDEX: CLOSED, MIDDLE: CLOSED, RING: CLOSED, LITTLE: CLOSED}, speed=SNAP)
            time.sleep(0.12)
        else:
            send_pose(driver, {THUMB_H: HALF, THUMB_V: HALF, MIDDLE: CLOSED, RING: CLOSED, LITTLE: CLOSED}, speed=SNAP)
            time.sleep(0.12)
            
        # Wave up
        if not SKIP_INDEX_MODE:
            send_pose(driver, {THUMB_H: OPEN, THUMB_V: OPEN, INDEX: CLOSED, MIDDLE: CLOSED, RING: CLOSED, LITTLE: CLOSED}, speed=SNAP)
            time.sleep(0.12)
            send_pose(driver, {THUMB_H: OPEN, THUMB_V: OPEN, INDEX: OPEN, MIDDLE: CLOSED, RING: CLOSED, LITTLE: CLOSED}, speed=SNAP)
            time.sleep(0.12)
        else:
            send_pose(driver, {THUMB_H: OPEN, THUMB_V: OPEN, MIDDLE: CLOSED, RING: CLOSED, LITTLE: CLOSED}, speed=SNAP)
            time.sleep(0.12)
            
        send_pose(driver, {THUMB_H: OPEN, THUMB_V: OPEN, INDEX: OPEN, MIDDLE: OPEN, RING: CLOSED, LITTLE: CLOSED}, speed=SNAP)
        time.sleep(0.12)
        send_pose(driver, {THUMB_H: OPEN, THUMB_V: OPEN, INDEX: OPEN, MIDDLE: OPEN, RING: OPEN, LITTLE: CLOSED}, speed=SNAP)
        time.sleep(0.12)
        send_pose(driver, {THUMB_H: OPEN, THUMB_V: OPEN, INDEX: OPEN, MIDDLE: OPEN, RING: OPEN, LITTLE: OPEN}, speed=SNAP)
        time.sleep(0.3)
    print("    ✓ Done!")


def counting_animation(driver):
    print("    🔢 Counting 1 to 5...")
    send_pose(driver, {THUMB_H: CLOSED, THUMB_V: CLOSED, INDEX: CLOSED, MIDDLE: CLOSED, RING: CLOSED, LITTLE: CLOSED}, speed=FAST)
    time.sleep(0.8)
    
    if not SKIP_INDEX_MODE:
        print("      1...")
        send_pose(driver, {THUMB_H: CLOSED, THUMB_V: CLOSED, INDEX: OPEN, MIDDLE: CLOSED, RING: CLOSED, LITTLE: CLOSED}, speed=SNAP)
        time.sleep(1.0)
        print("      2...")
        send_pose(driver, {THUMB_H: CLOSED, THUMB_V: CLOSED, INDEX: OPEN, MIDDLE: OPEN, RING: CLOSED, LITTLE: CLOSED}, speed=SNAP)
        time.sleep(1.0)
        print("      3...")
        send_pose(driver, {THUMB_H: CLOSED, THUMB_V: CLOSED, INDEX: OPEN, MIDDLE: OPEN, RING: OPEN, LITTLE: CLOSED}, speed=SNAP)
        time.sleep(1.0)
        print("      4...")
        send_pose(driver, {THUMB_H: CLOSED, THUMB_V: CLOSED, INDEX: OPEN, MIDDLE: OPEN, RING: OPEN, LITTLE: OPEN}, speed=SNAP)
        time.sleep(1.0)
    else:
        # Adapted 5-finger counting
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
    send_pose(driver, {THUMB_H: OPEN, THUMB_V: OPEN, INDEX: OPEN, MIDDLE: OPEN, RING: OPEN, LITTLE: OPEN}, speed=SNAP)
    time.sleep(1.5)
    print("    ✓ Done!")


def grab_release_animation(driver):
    print("    🫳 Grab & Release...")
    send_pose(driver, {THUMB_H: OPEN, THUMB_V: OPEN, INDEX: OPEN, MIDDLE: OPEN, RING: OPEN, LITTLE: OPEN}, speed=NORMAL)
    time.sleep(1.0)
    send_pose(driver, {THUMB_H: SLIGHT, THUMB_V: SLIGHT, INDEX: SLIGHT, MIDDLE: SLIGHT, RING: SLIGHT, LITTLE: SLIGHT}, speed=SLOW)
    time.sleep(0.8)
    send_pose(driver, {THUMB_H: MOSTLY, THUMB_V: MOSTLY, INDEX: MOSTLY, MIDDLE: MOSTLY, RING: MOSTLY, LITTLE: MOSTLY}, speed=SLOW)
    time.sleep(0.5)
    send_pose(driver, {THUMB_H: CLOSED, THUMB_V: CLOSED, INDEX: CLOSED, MIDDLE: CLOSED, RING: CLOSED, LITTLE: CLOSED}, speed=SLOW)
    time.sleep(2.0)
    send_pose(driver, {THUMB_H: HALF, THUMB_V: HALF, INDEX: HALF, MIDDLE: HALF, RING: HALF, LITTLE: HALF}, speed=SLOW)
    time.sleep(0.4)
    send_pose(driver, {THUMB_H: OPEN, THUMB_V: OPEN, INDEX: OPEN, MIDDLE: OPEN, RING: OPEN, LITTLE: OPEN}, speed=SLOW)
    time.sleep(1.0)
    print("    ✓ Done!")


def finger_tap_animation(driver):
    print("    🎹 Finger tapping...")
    send_pose(driver, {THUMB_H: SLIGHT, THUMB_V: SLIGHT, INDEX: OPEN, MIDDLE: OPEN, RING: OPEN, LITTLE: OPEN}, speed=FAST)
    time.sleep(0.5)
    for _ in range(4):
        send_pose(driver, {THUMB_H: SLIGHT, THUMB_V: SLIGHT, INDEX: OPEN, MIDDLE: OPEN, RING: OPEN, LITTLE: HALF}, speed=SNAP)
        time.sleep(0.1)
        send_pose(driver, {THUMB_H: SLIGHT, THUMB_V: SLIGHT, INDEX: OPEN, MIDDLE: OPEN, RING: OPEN, LITTLE: OPEN}, speed=SNAP)
        time.sleep(0.06)
        send_pose(driver, {THUMB_H: SLIGHT, THUMB_V: SLIGHT, INDEX: OPEN, MIDDLE: OPEN, RING: HALF, LITTLE: OPEN}, speed=SNAP)
        time.sleep(0.1)
        send_pose(driver, {THUMB_H: SLIGHT, THUMB_V: SLIGHT, INDEX: OPEN, MIDDLE: OPEN, RING: OPEN, LITTLE: OPEN}, speed=SNAP)
        time.sleep(0.06)
        send_pose(driver, {THUMB_H: SLIGHT, THUMB_V: SLIGHT, INDEX: OPEN, MIDDLE: HALF, RING: OPEN, LITTLE: OPEN}, speed=SNAP)
        time.sleep(0.1)
        send_pose(driver, {THUMB_H: SLIGHT, THUMB_V: SLIGHT, INDEX: OPEN, MIDDLE: OPEN, RING: OPEN, LITTLE: OPEN}, speed=SNAP)
        time.sleep(0.06)
        if not SKIP_INDEX_MODE:
            send_pose(driver, {THUMB_H: SLIGHT, THUMB_V: SLIGHT, INDEX: HALF, MIDDLE: OPEN, RING: OPEN, LITTLE: OPEN}, speed=SNAP)
            time.sleep(0.1)
            send_pose(driver, {THUMB_H: SLIGHT, THUMB_V: SLIGHT, INDEX: OPEN, MIDDLE: OPEN, RING: OPEN, LITTLE: OPEN}, speed=SNAP)
            time.sleep(0.12)
        else:
            time.sleep(0.12)
    print("    ✓ Done!")


def handshake_animation(driver):
    print("    🤝 Handshake...")
    send_pose(driver, {THUMB_H: OPEN, THUMB_V: OPEN, INDEX: OPEN, MIDDLE: OPEN, RING: OPEN, LITTLE: OPEN}, speed=NORMAL)
    time.sleep(1.0)
    send_pose(driver, {THUMB_H: HALF, THUMB_V: HALF, INDEX: MOSTLY, MIDDLE: MOSTLY, RING: MOSTLY, LITTLE: MOSTLY}, speed=NORMAL)
    time.sleep(0.5)
    for _ in range(3):
        send_pose(driver, {THUMB_H: SLIGHT, THUMB_V: SLIGHT, INDEX: HALF, MIDDLE: HALF, RING: HALF, LITTLE: HALF}, speed=FAST)
        time.sleep(0.3)
        send_pose(driver, {THUMB_H: HALF, THUMB_V: HALF, INDEX: MOSTLY, MIDDLE: MOSTLY, RING: MOSTLY, LITTLE: MOSTLY}, speed=FAST)
        time.sleep(0.3)
    time.sleep(0.3)
    send_pose(driver, {THUMB_H: OPEN, THUMB_V: OPEN, INDEX: OPEN, MIDDLE: OPEN, RING: OPEN, LITTLE: OPEN}, speed=SLOW)
    time.sleep(1.0)
    print("    ✓ Done!")


# ═══════════════════════════════════════════════════════════════════════════
# Gesture Definitions Generator
# ═══════════════════════════════════════════════════════════════════════════

def get_actions():
    """Generates actions list dynamically based on skipping index or not."""
    return [
        ("a", "🖐  OPEN HAND",         "All fingers fully extended",
         "pose", {THUMB_H: OPEN, THUMB_V: OPEN, INDEX: OPEN, MIDDLE: OPEN, RING: OPEN, LITTLE: OPEN},
         NORMAL, FIRM),

        ("b", "✊  FIST",              "All fingers closed tight",
         "pose", {THUMB_H: CLOSED, THUMB_V: CLOSED, INDEX: CLOSED, MIDDLE: CLOSED, RING: CLOSED, LITTLE: CLOSED},
         NORMAL, STRONG),

        ("c", "👍  THUMBS UP",         "Thumb up, others closed",
         "pose", {THUMB_H: OPEN, THUMB_V: OPEN, INDEX: CLOSED, MIDDLE: CLOSED, RING: CLOSED, LITTLE: CLOSED},
         FAST, FIRM),

        ("d", "👎  THUMBS DOWN",       "Everything curled in",
         "pose", {THUMB_H: CLOSED, THUMB_V: CLOSED, INDEX: CLOSED, MIDDLE: CLOSED, RING: CLOSED, LITTLE: CLOSED},
         FAST, FIRM),

        ("e", "🤏  PINCH GRIP",
         "Thumb + index precision pinch" if not SKIP_INDEX_MODE else "Thumb + middle precision pinch",
         "pose", {THUMB_H: MOSTLY, THUMB_V: MOSTLY, INDEX: MOSTLY, MIDDLE: OPEN if not SKIP_INDEX_MODE else MOSTLY, RING: SLIGHT, LITTLE: SLIGHT},
         SLOW, GENTLE),

        ("f", "🤘  ROCK ON",           "Horns gesture (index + pinky up)" if not SKIP_INDEX_MODE else "Horns (middle + pinky up)",
         "pose", {THUMB_H: CLOSED, THUMB_V: CLOSED, INDEX: OPEN if not SKIP_INDEX_MODE else CLOSED, MIDDLE: CLOSED if not SKIP_INDEX_MODE else OPEN, RING: CLOSED, LITTLE: OPEN},
         FAST, FIRM),

        ("g", "🤙  CALL ME / SHAKA",   "Thumb + pinky extended",
         "pose", {THUMB_H: OPEN, THUMB_V: OPEN, INDEX: CLOSED, MIDDLE: CLOSED, RING: CLOSED, LITTLE: OPEN},
         FAST, FIRM),

        ("h", "3️⃣   THREE",
         "Index + Middle + Ring up" if not SKIP_INDEX_MODE else "Middle + Ring + Little up",
         "pose", {THUMB_H: CLOSED, THUMB_V: CLOSED, INDEX: OPEN if not SKIP_INDEX_MODE else CLOSED, MIDDLE: OPEN, RING: OPEN, LITTLE: CLOSED if not SKIP_INDEX_MODE else OPEN},
         FAST, FIRM),

        ("i", "👆  POINT",             "Index pointing forward" if not SKIP_INDEX_MODE else "Middle pointing forward",
         "pose", {THUMB_H: CLOSED, THUMB_V: CLOSED, INDEX: OPEN if not SKIP_INDEX_MODE else CLOSED, MIDDLE: CLOSED if not SKIP_INDEX_MODE else OPEN, RING: CLOSED, LITTLE: CLOSED},
         FAST, FIRM),

        ("j", "👌  OK SIGN",           "Thumb + index circle" if not SKIP_INDEX_MODE else "Thumb + middle circle",
         "pose", {THUMB_H: MOSTLY, THUMB_V: MOSTLY, INDEX: MOSTLY if not SKIP_INDEX_MODE else OPEN, MIDDLE: OPEN if not SKIP_INDEX_MODE else MOSTLY, RING: OPEN, LITTLE: OPEN},
         NORMAL, FIRM),

        ("k", "😌  NATURAL REST",      "Relaxed, slightly curled",
         "pose", {THUMB_H: SLIGHT, THUMB_V: SLIGHT, INDEX: SLIGHT, MIDDLE: SLIGHT, RING: SLIGHT, LITTLE: SLIGHT},
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


def print_menu(actions):
    print()
    print("═" * 60)
    print("  🤖  HITBOT eHand-6 — LIVE DEMO")
    print("═" * 60)
    print()
    print("  ┌────────────────────────────────────────────────────┐")
    print("  │  INSTANT GESTURES                                 │")
    print("  ├────────────────────────────────────────────────────┤")

    for key, name, desc, typ, *_ in actions:
        if typ == "pose":
            print(f"  │  [ {key} ]  {name:38s}  │")

    print("  ├────────────────────────────────────────────────────┤")
    print("  │  ANIMATED SEQUENCES                               │")
    print("  ├────────────────────────────────────────────────────┤")

    for key, name, desc, typ, *_ in actions:
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
    if SKIP_INDEX_MODE:
        print("  ⚠  Index finger (Motor 3) bypassed — defect mode")
    else:
        print("  ✓  Full 6-Finger Control Mode Active")
    print("  📡 Press any key a–p to go!")
    print()


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

def main():
    global WORKING_MOTORS, SKIP_INDEX_MODE
    
    parser = argparse.ArgumentParser(description="eHand-6 Live Demo")
    parser.add_argument("--channel", default="can0")
    parser.add_argument("--hand", choices=["left", "right", "auto"], default="auto")
    parser.add_argument("--skip-index", action="store_true", help="Force skipping index finger (Motor 3)")
    parser.add_argument("--skip-cal", action="store_true", help="Skip calibration")
    args = parser.parse_args()

    SKIP_INDEX_MODE = args.skip_index
    if SKIP_INDEX_MODE:
        WORKING_MOTORS = [1, 2, 4, 5, 6]
    else:
        WORKING_MOTORS = [1, 2, 3, 4, 5, 6]

    hand_id = None
    if args.hand == "right":
        hand_id = HandID.RIGHT
    elif args.hand == "left":
        hand_id = HandID.LEFT
    else:
        # Auto-detect Hand ID (Left 0x12 or Right 0x11)
        print("🔍 Scanning CAN bus for hand ID...")
        for test_id in [HandID.LEFT, HandID.RIGHT]:
            driver = EHand6Driver(channel=args.channel, hand_id=test_id)
            try:
                driver.connect()
                status = driver.read_status()
                driver.disconnect()
                if status is not None:
                    hand_id = test_id
                    print(f"  ✓ Hand detected at ID 0x{hand_id:02X} ({'LEFT' if hand_id == HandID.LEFT else 'RIGHT'})")
                    break
            except Exception:
                pass
        
        if hand_id is None:
            print("\n  ✗ Auto-detection failed: No hand responded on ID 0x11 or 0x12!")
            print("    Please check that the hand is powered, connected, and your CAN is up: sudo ./setup_can.sh")
            sys.exit(1)

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

    actions = get_actions()

    # Build lookup dicts for fast key handling
    pose_map = {}
    for key, name, desc, typ, positions, speed, torque in actions:
        if typ == "pose":
            pose_map[key] = (name, desc, positions, speed, torque)

    clear_screen()
    print_menu(actions)

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
                print_menu(actions)
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
                for ak, aname, adesc, *_ in actions:
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
