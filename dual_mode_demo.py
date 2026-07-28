#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════
  HITBOT eHand-6 — DUAL-MODE DEMO (MANUAL & AUTONOMOUS)
═══════════════════════════════════════════════════════════════════════════

  This is a new script that provides both MANUAL keyboard-driven control
  and AUTONOMOUS continuous sequence play.

  Usage:
      python3 dual_mode_demo.py
      python3 dual_mode_demo.py --mode auto
      python3 dual_mode_demo.py --skip-index
      python3 dual_mode_demo.py --skip-cal

  Keys:
      - [ x ] : Toggle between MANUAL and AUTONOMOUS modes
      - [ a–p ] : Trigger individual gestures (in MANUAL mode)
      - [ z ] : Re-calibrate the hand
      - [ SPC ] : Emergency stop
      - [ q / ESC ] : Quit

═══════════════════════════════════════════════════════════════════════════
"""

import sys
import time
import os
import argparse
import threading
import queue

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
# Global parameters
# ═══════════════════════════════════════════════════════════════════════════
WORKING_MOTORS = [1, 2, 3, 4, 5, 6]
SKIP_INDEX_MODE = False
key_queue = queue.Queue()


# ═══════════════════════════════════════════════════════════════════════════
# Keyboard Listener Thread
# ═══════════════════════════════════════════════════════════════════════════
def keyboard_listener():
    """Background thread to read keys and put them into a thread-safe queue."""
    while True:
        try:
            key = readchar.readkey()
            key_queue.put(key)
        except Exception:
            break


# ═══════════════════════════════════════════════════════════════════════════
# Core Control Utilities
# ═══════════════════════════════════════════════════════════════════════════

def send_pose(driver, positions, speed=NORMAL, torque=FIRM):
    fingers = {}
    for mid in WORKING_MOTORS:
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
# Check for E-Stop/Mode Interrupts during Delays
# ═══════════════════════════════════════════════════════════════════════════
def check_interrupts(driver, duration_sec):
    """
    Sleeps for duration_sec in small steps, polling the key queue.
    Returns:
        - "stop" if Emergency Stop is pressed.
        - "quit" if Quit is pressed.
        - "toggle" if Toggle Mode is pressed.
        - None if delay completes without interrupt.
    """
    steps = int(duration_sec * 10)
    for _ in range(steps):
        time.sleep(0.1)
        if not key_queue.empty():
            k = key_queue.queue[0]  # Peek at the queue
            if k == ' ':
                key_queue.get()  # consume key
                driver.emergency_stop()
                return "stop"
            elif k in (readchar.key.ESC, 'q', 'Q'):
                key_queue.get()  # consume key
                return "quit"
            elif k in ('x', 'X'):
                key_queue.get()  # consume key
                return "toggle"
    return None


# ═══════════════════════════════════════════════════════════════════════════
# Animated sequences with built-in interrupt checks
# ═══════════════════════════════════════════════════════════════════════════

def wave_animation(driver):
    print("    🌊 Waving...")
    send_pose(driver, {THUMB_H: OPEN, THUMB_V: OPEN, INDEX: OPEN, MIDDLE: OPEN, RING: OPEN, LITTLE: OPEN}, speed=FAST)
    res = check_interrupts(driver, 0.5)
    if res: return res
    
    for _ in range(3):
        # Wave down
        send_pose(driver, {THUMB_H: OPEN, THUMB_V: OPEN, INDEX: OPEN, MIDDLE: OPEN, RING: OPEN, LITTLE: HALF}, speed=SNAP)
        res = check_interrupts(driver, 0.12)
        if res: return res
        send_pose(driver, {THUMB_H: OPEN, THUMB_V: OPEN, INDEX: OPEN, MIDDLE: OPEN, RING: HALF, LITTLE: CLOSED}, speed=SNAP)
        res = check_interrupts(driver, 0.12)
        if res: return res
        send_pose(driver, {THUMB_H: OPEN, THUMB_V: OPEN, INDEX: OPEN, MIDDLE: HALF, RING: CLOSED, LITTLE: CLOSED}, speed=SNAP)
        res = check_interrupts(driver, 0.12)
        if res: return res
        
        if not SKIP_INDEX_MODE:
            send_pose(driver, {THUMB_H: OPEN, THUMB_V: OPEN, INDEX: HALF, MIDDLE: CLOSED, RING: CLOSED, LITTLE: CLOSED}, speed=SNAP)
            res = check_interrupts(driver, 0.12)
            if res: return res
            send_pose(driver, {THUMB_H: HALF, THUMB_V: HALF, INDEX: CLOSED, MIDDLE: CLOSED, RING: CLOSED, LITTLE: CLOSED}, speed=SNAP)
            res = check_interrupts(driver, 0.12)
            if res: return res
        else:
            send_pose(driver, {THUMB_H: HALF, THUMB_V: HALF, MIDDLE: CLOSED, RING: CLOSED, LITTLE: CLOSED}, speed=SNAP)
            res = check_interrupts(driver, 0.12)
            if res: return res
            
        # Wave up
        if not SKIP_INDEX_MODE:
            send_pose(driver, {THUMB_H: OPEN, THUMB_V: OPEN, INDEX: CLOSED, MIDDLE: CLOSED, RING: CLOSED, LITTLE: CLOSED}, speed=SNAP)
            res = check_interrupts(driver, 0.12)
            if res: return res
            send_pose(driver, {THUMB_H: OPEN, THUMB_V: OPEN, INDEX: OPEN, MIDDLE: CLOSED, RING: CLOSED, LITTLE: CLOSED}, speed=SNAP)
            res = check_interrupts(driver, 0.12)
            if res: return res
        else:
            send_pose(driver, {THUMB_H: OPEN, THUMB_V: OPEN, MIDDLE: CLOSED, RING: CLOSED, LITTLE: CLOSED}, speed=SNAP)
            res = check_interrupts(driver, 0.12)
            if res: return res
            
        send_pose(driver, {THUMB_H: OPEN, THUMB_V: OPEN, INDEX: OPEN, MIDDLE: OPEN, RING: CLOSED, LITTLE: CLOSED}, speed=SNAP)
        res = check_interrupts(driver, 0.12)
        if res: return res
        send_pose(driver, {THUMB_H: OPEN, THUMB_V: OPEN, INDEX: OPEN, MIDDLE: OPEN, RING: OPEN, LITTLE: CLOSED}, speed=SNAP)
        res = check_interrupts(driver, 0.12)
        if res: return res
        send_pose(driver, {THUMB_H: OPEN, THUMB_V: OPEN, INDEX: OPEN, MIDDLE: OPEN, RING: OPEN, LITTLE: OPEN}, speed=SNAP)
        res = check_interrupts(driver, 0.3)
        if res: return res
        
    print("    ✓ Done!")
    return None


def counting_animation(driver):
    print("    🔢 Counting 1 to 5...")
    send_pose(driver, {THUMB_H: CLOSED, THUMB_V: CLOSED, INDEX: CLOSED, MIDDLE: CLOSED, RING: CLOSED, LITTLE: CLOSED}, speed=FAST)
    res = check_interrupts(driver, 0.8)
    if res: return res
    
    if not SKIP_INDEX_MODE:
        print("      1...")
        send_pose(driver, {THUMB_H: CLOSED, THUMB_V: CLOSED, INDEX: OPEN, MIDDLE: CLOSED, RING: CLOSED, LITTLE: CLOSED}, speed=SNAP)
        res = check_interrupts(driver, 1.0)
        if res: return res
        print("      2...")
        send_pose(driver, {THUMB_H: CLOSED, THUMB_V: CLOSED, INDEX: OPEN, MIDDLE: OPEN, RING: CLOSED, LITTLE: CLOSED}, speed=SNAP)
        res = check_interrupts(driver, 1.0)
        if res: return res
        print("      3...")
        send_pose(driver, {THUMB_H: CLOSED, THUMB_V: CLOSED, INDEX: OPEN, MIDDLE: OPEN, RING: OPEN, LITTLE: CLOSED}, speed=SNAP)
        res = check_interrupts(driver, 1.0)
        if res: return res
        print("      4...")
        send_pose(driver, {THUMB_H: CLOSED, THUMB_V: CLOSED, INDEX: OPEN, MIDDLE: OPEN, RING: OPEN, LITTLE: OPEN}, speed=SNAP)
        res = check_interrupts(driver, 1.0)
        if res: return res
    else:
        print("      1...")
        send_pose(driver, {THUMB_H: CLOSED, THUMB_V: CLOSED, MIDDLE: OPEN, RING: CLOSED, LITTLE: CLOSED}, speed=SNAP)
        res = check_interrupts(driver, 1.0)
        if res: return res
        print("      2...")
        send_pose(driver, {THUMB_H: CLOSED, THUMB_V: CLOSED, MIDDLE: OPEN, RING: OPEN, LITTLE: CLOSED}, speed=SNAP)
        res = check_interrupts(driver, 1.0)
        if res: return res
        print("      3...")
        send_pose(driver, {THUMB_H: CLOSED, THUMB_V: CLOSED, MIDDLE: OPEN, RING: OPEN, LITTLE: OPEN}, speed=SNAP)
        res = check_interrupts(driver, 1.0)
        if res: return res
        print("      4...")
        send_pose(driver, {THUMB_H: OPEN, THUMB_V: CLOSED, MIDDLE: OPEN, RING: OPEN, LITTLE: OPEN}, speed=SNAP)
        res = check_interrupts(driver, 1.0)
        if res: return res
        
    print("      5!")
    send_pose(driver, {THUMB_H: OPEN, THUMB_V: OPEN, INDEX: OPEN, MIDDLE: OPEN, RING: OPEN, LITTLE: OPEN}, speed=SNAP)
    res = check_interrupts(driver, 1.5)
    if res: return res
    print("    ✓ Done!")
    return None


def grab_release_animation(driver):
    print("    🫳 Grab & Release...")
    send_pose(driver, {THUMB_H: OPEN, THUMB_V: OPEN, INDEX: OPEN, MIDDLE: OPEN, RING: OPEN, LITTLE: OPEN}, speed=NORMAL)
    res = check_interrupts(driver, 1.0)
    if res: return res
    send_pose(driver, {THUMB_H: SLIGHT, THUMB_V: SLIGHT, INDEX: SLIGHT, MIDDLE: SLIGHT, RING: SLIGHT, LITTLE: SLIGHT}, speed=SLOW)
    res = check_interrupts(driver, 0.8)
    if res: return res
    send_pose(driver, {THUMB_H: MOSTLY, THUMB_V: MOSTLY, INDEX: MOSTLY, MIDDLE: MOSTLY, RING: MOSTLY, LITTLE: MOSTLY}, speed=SLOW)
    res = check_interrupts(driver, 0.5)
    if res: return res
    send_pose(driver, {THUMB_H: CLOSED, THUMB_V: CLOSED, INDEX: CLOSED, MIDDLE: CLOSED, RING: CLOSED, LITTLE: CLOSED}, speed=SLOW)
    res = check_interrupts(driver, 2.0)
    if res: return res
    send_pose(driver, {THUMB_H: HALF, THUMB_V: HALF, INDEX: HALF, MIDDLE: HALF, RING: HALF, LITTLE: HALF}, speed=SLOW)
    res = check_interrupts(driver, 0.4)
    if res: return res
    send_pose(driver, {THUMB_H: OPEN, THUMB_V: OPEN, INDEX: OPEN, MIDDLE: OPEN, RING: OPEN, LITTLE: OPEN}, speed=SLOW)
    res = check_interrupts(driver, 1.0)
    if res: return res
    print("    ✓ Done!")
    return None


def finger_tap_animation(driver):
    print("    🎹 Finger tapping...")
    send_pose(driver, {THUMB_H: SLIGHT, THUMB_V: SLIGHT, INDEX: OPEN, MIDDLE: OPEN, RING: OPEN, LITTLE: OPEN}, speed=FAST)
    res = check_interrupts(driver, 0.5)
    if res: return res
    for _ in range(4):
        send_pose(driver, {THUMB_H: SLIGHT, THUMB_V: SLIGHT, INDEX: OPEN, MIDDLE: OPEN, RING: OPEN, LITTLE: HALF}, speed=SNAP)
        res = check_interrupts(driver, 0.1)
        if res: return res
        send_pose(driver, {THUMB_H: SLIGHT, THUMB_V: SLIGHT, INDEX: OPEN, MIDDLE: OPEN, RING: OPEN, LITTLE: OPEN}, speed=SNAP)
        res = check_interrupts(driver, 0.06)
        if res: return res
        send_pose(driver, {THUMB_H: SLIGHT, THUMB_V: SLIGHT, INDEX: OPEN, MIDDLE: OPEN, RING: HALF, LITTLE: OPEN}, speed=SNAP)
        res = check_interrupts(driver, 0.1)
        if res: return res
        send_pose(driver, {THUMB_H: SLIGHT, THUMB_V: SLIGHT, INDEX: OPEN, MIDDLE: OPEN, RING: OPEN, LITTLE: OPEN}, speed=SNAP)
        res = check_interrupts(driver, 0.06)
        if res: return res
        send_pose(driver, {THUMB_H: SLIGHT, THUMB_V: SLIGHT, INDEX: OPEN, MIDDLE: HALF, RING: OPEN, LITTLE: OPEN}, speed=SNAP)
        res = check_interrupts(driver, 0.1)
        if res: return res
        send_pose(driver, {THUMB_H: SLIGHT, THUMB_V: SLIGHT, INDEX: OPEN, MIDDLE: OPEN, RING: OPEN, LITTLE: OPEN}, speed=SNAP)
        res = check_interrupts(driver, 0.06)
        if res: return res
        
        if not SKIP_INDEX_MODE:
            send_pose(driver, {THUMB_H: SLIGHT, THUMB_V: SLIGHT, INDEX: HALF, MIDDLE: OPEN, RING: OPEN, LITTLE: OPEN}, speed=SNAP)
            res = check_interrupts(driver, 0.1)
            if res: return res
            send_pose(driver, {THUMB_H: SLIGHT, THUMB_V: SLIGHT, INDEX: OPEN, MIDDLE: OPEN, RING: OPEN, LITTLE: OPEN}, speed=SNAP)
            res = check_interrupts(driver, 0.12)
            if res: return res
        else:
            res = check_interrupts(driver, 0.12)
            if res: return res
    print("    ✓ Done!")
    return None


def handshake_animation(driver):
    print("    🤝 Handshake...")
    send_pose(driver, {THUMB_H: OPEN, THUMB_V: OPEN, INDEX: OPEN, MIDDLE: OPEN, RING: OPEN, LITTLE: OPEN}, speed=NORMAL)
    res = check_interrupts(driver, 1.0)
    if res: return res
    send_pose(driver, {THUMB_H: HALF, THUMB_V: HALF, INDEX: MOSTLY, MIDDLE: MOSTLY, RING: MOSTLY, LITTLE: MOSTLY}, speed=NORMAL)
    res = check_interrupts(driver, 0.5)
    if res: return res
    for _ in range(3):
        send_pose(driver, {THUMB_H: SLIGHT, THUMB_V: SLIGHT, INDEX: HALF, MIDDLE: HALF, RING: HALF, LITTLE: HALF}, speed=FAST)
        res = check_interrupts(driver, 0.3)
        if res: return res
        send_pose(driver, {THUMB_H: HALF, THUMB_V: HALF, INDEX: MOSTLY, MIDDLE: MOSTLY, RING: MOSTLY, LITTLE: MOSTLY}, speed=FAST)
        res = check_interrupts(driver, 0.3)
        if res: return res
    res = check_interrupts(driver, 0.3)
    if res: return res
    send_pose(driver, {THUMB_H: OPEN, THUMB_V: OPEN, INDEX: OPEN, MIDDLE: OPEN, RING: OPEN, LITTLE: OPEN}, speed=SLOW)
    res = check_interrupts(driver, 1.0)
    if res: return res
    print("    ✓ Done!")
    return None


# ═══════════════════════════════════════════════════════════════════════════
# Gesture Definitions
# ═══════════════════════════════════════════════════════════════════════════
def get_actions():
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
         "anim", wave_animation, None, None),

        ("m", "🔢  COUNT 1-5",         "Counts with fingers one by one",
         "anim", counting_animation, None, None),

        ("n", "🫳  GRAB & RELEASE",    "Pick up & release invisible object",
         "anim", grab_release_animation, None, None),

        ("o", "🎹  FINGER TAP",        "Impatient drumming on table",
         "anim", finger_tap_animation, None, None),

        ("p", "🤝  HANDSHAKE",         "Grip, pump, and release",
         "anim", handshake_animation, None, None),
    ]


# ═══════════════════════════════════════════════════════════════════════════
# Display Function
# ═══════════════════════════════════════════════════════════════════════════
def clear_screen():
    os.system('clear' if os.name != 'nt' else 'cls')


def print_status_bar(mode_str, hand_str):
    print("═" * 60)
    print(f"  🤖  HITBOT DUAL-MODE DEMO  |  Hand: {hand_str}")
    print(f"  [ MODE: {mode_str} ]")
    print("═" * 60)
    print("  CONTROLS:")
    print("    [ x ] : Toggle MANUAL / AUTONOMOUS Mode")
    print("    [ z ] : Re-calibrate")
    print("    [SPC] : Emergency Stop (Disable motors)")
    print("    [ q ] : Quit / Exit")
    print("─" * 60)


def print_manual_menu(actions):
    print("  MANUAL MODE — Press key (a–p) to trigger gesture:")
    for key, name, desc, typ, *_ in actions:
        print(f"    [ {key} ]  {name:30s} - {desc}")
    print()


def print_auto_status(current_gesture_name):
    print("  AUTONOMOUS MODE — Executing sequence continuously one-by-one...")
    print(f"  ▶ Active: {current_gesture_name}")
    print("  (Press [x] to return to Manual mode, [SPC] to E-stop)")
    print()


# ═══════════════════════════════════════════════════════════════════════════
# Main Routine
# ═══════════════════════════════════════════════════════════════════════════

def main():
    global WORKING_MOTORS, SKIP_INDEX_MODE
    
    parser = argparse.ArgumentParser(description="eHand-6 Dual-Mode Demo")
    parser.add_argument("--channel", default="can0")
    parser.add_argument("--hand", choices=["left", "right", "auto"], default="auto")
    parser.add_argument("--mode", choices=["manual", "auto"], default="manual")
    parser.add_argument("--skip-index", action="store_true", help="Skip index finger")
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
        print("🔍 Scanning CAN bus for hand ID...")
        for test_id in [HandID.LEFT, HandID.RIGHT]:
            test_driver = EHand6Driver(channel=args.channel, hand_id=test_id)
            try:
                test_driver.connect()
                status = test_driver.read_status()
                test_driver.disconnect()
                if status is not None:
                    hand_id = test_id
                    print(f"  ✓ Hand detected at ID 0x{hand_id:02X} ({'LEFT' if hand_id == HandID.LEFT else 'RIGHT'})")
                    break
            except Exception:
                pass
        
        if hand_id is None:
            print("\n  ✗ Auto-detection failed: No hand responded on ID 0x11 or 0x12!")
            print("    Please run: sudo ./setup_can.sh")
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

    # Start keyboard listener background thread
    listener_thread = threading.Thread(target=keyboard_listener, daemon=True)
    listener_thread.start()

    actions = get_actions()
    pose_map = {key: (name, desc, pos, speed, torque) for key, name, desc, typ, pos, speed, torque in actions if typ == "pose"}
    anim_map = {key: (name, desc, func) for key, name, desc, typ, func, *_ in actions if typ == "anim"}

    mode = args.mode  # "manual" or "auto"
    hand_str = "LEFT (0x12)" if hand_id == HandID.LEFT else "RIGHT (0x11)"
    
    current_auto_index = 0
    
    # Empty queue from any accidental start keys
    while not key_queue.empty():
        key_queue.get()

    try:
        while True:
            # ────────────────────────────────────────────────────────────────
            # MANUAL MODE
            # ────────────────────────────────────────────────────────────────
            if mode == "manual":
                clear_screen()
                print_status_bar("MANUAL", hand_str)
                print_manual_menu(actions)
                
                # Wait for keyboard inputs (blocking read from queue)
                key = key_queue.get()
                
                # Check control commands
                if key in (readchar.key.ESC, 'q', 'Q'):
                    print("\n  🚪 Exiting...")
                    break
                elif key == ' ':
                    driver.emergency_stop()
                    print("\n  🛑 EMERGENCY STOP! All motors disabled.")
                    print("  Press [z] to calibrate & resume, or [q] to quit.")
                    # Keep disabled until user re-calibrates or exits
                    while True:
                        k = key_queue.get()
                        if k in ('z', 'Z'):
                            calibrate(driver)
                            break
                        elif k in (readchar.key.ESC, 'q', 'Q'):
                            raise KeyboardInterrupt
                    continue
                elif key in ('z', 'Z'):
                    calibrate(driver)
                    continue
                elif key in ('x', 'X'):
                    mode = "auto"
                    continue
                
                # Perform selected action
                k = key.lower()
                if k in pose_map:
                    name, desc, positions, speed, torque = pose_map[k]
                    send_pose(driver, positions, speed=speed, torque=torque)
                    time.sleep(0.5)
                elif k in anim_map:
                    name, desc, func = anim_map[k]
                    func(driver)
                    time.sleep(0.5)

            # ────────────────────────────────────────────────────────────────
            # AUTONOMOUS MODE
            # ────────────────────────────────────────────────────────────────
            elif mode == "auto":
                action_item = actions[current_auto_index]
                key_char, name, desc, typ = action_item[0], action_item[1], action_item[2], action_item[3]
                
                clear_screen()
                print_status_bar("AUTONOMOUS (LOOPING)", hand_str)
                print_auto_status(name)
                
                interrupt_status = None
                
                if typ == "pose":
                    positions, speed, torque = action_item[4], action_item[5], action_item[6]
                    send_pose(driver, positions, speed=speed, torque=torque)
                    # Hold pose for 1.8 seconds while checking for keys
                    interrupt_status = check_interrupts(driver, 1.8)
                elif typ == "anim":
                    func = action_item[4]
                    interrupt_status = func(driver)
                    if interrupt_status is None:
                        # Wait 1.0s between animations
                        interrupt_status = check_interrupts(driver, 1.0)

                # Check if user interrupted execution
                if interrupt_status == "stop":
                    print("\n  🛑 EMERGENCY STOP! All motors disabled.")
                    print("  Press [z] to calibrate & resume, or [q] to quit.")
                    while True:
                        k = key_queue.get()
                        if k in ('z', 'Z'):
                            calibrate(driver)
                            break
                        elif k in (readchar.key.ESC, 'q', 'Q'):
                            raise KeyboardInterrupt
                    continue
                elif interrupt_status == "quit":
                    print("\n  🚪 Exiting...")
                    break
                elif interrupt_status == "toggle":
                    print("\n  Toggle back to Manual mode...")
                    mode = "manual"
                    time.sleep(0.5)
                    continue
                
                # Advance to next gesture in the list
                current_auto_index = (current_auto_index + 1) % len(actions)

    except KeyboardInterrupt:
        print("\n\n  ⚠ Interrupted!")
    finally:
        print("  Stopping motors...")
        try:
            driver.emergency_stop()
        except Exception:
            pass
        driver.disconnect()
        print("\n  ✓ Done! Demo completed successfully. 🎉\n")


if __name__ == "__main__":
    main()
