# HITBOT eHand-6 CAN FD Control System

Control the HITBOT eHand-6 dexterous robotic hand via CAN FD using an MKS CANable V2.0 USB-to-CAN adapter on Linux.

This repository contains the complete driver stack, verification tests, interactive controllers, and diagnostic tools to connect, calibrate, and operate the eHand-6 directly from your laptop.

---

## 1. System Overview & Architecture

```
  ┌───────────┐         USB         ┌───────────────┐
  │           │ ──────────────────► │  MKS CANable  │ ───┐
  │ PC/Laptop │                     │  V2.0 Adapter │    │
  │  (Linux)  │ ◄────────────────── │ (Candlelight) │    │
  └───────────┘                     └───────────────┘    │ CAN FD Bus
        ▲                                                ├──────────────► ┌───────────┐
        │                                                │                │           │
        └────────────── Telemetry Feedback ──────────────┼──────────────  │  eHand-6  │
                                                         │                │           │
                                    ┌───────────────┐    │                └───────────┘
                                    │ 24V DC (3A+)  │ ───┘
                                    │ Power Supply  │
                                    └───────────────┘
```

### Cable Pinout (Official Manual)

| M8 Wire Color | Connection | Description |
| :---: | :--- | :--- |
| **Brown** | **+24VDC ±10%** | Main power input (draws ~3A peak) |
| **Blue** | **GND / 0V** | Power supply ground |
| **Black** | **CAN_H** | CAN high-speed differential signal |
| **White** | **CAN_L** | CAN low-speed differential signal |

*Note: Make sure to connect the CANable GND terminal to the 24V PSU GND terminal for a shared signal reference. Verify that the 120Ω termination jumper (marked `TERM` or `120R`) is enabled on the CANable.*

---

## 2. Quick Start

### 1. Install Dependencies
Ensure you have the Linux CAN utilities and the Python CAN interface library installed:
```bash
sudo apt update
sudo apt install -y can-utils iproute2
pip3 install python-can
```

### 2. Set Up SocketCAN Network
Connect the CANable V2.0 to your laptop. Bring up the interface with CAN FD enabled at **1 Mbps arbitration rate** and **5 Mbps data phase rate**:
```bash
sudo ./setup_can.sh
```

### 3. Verify Connection
Run the connection script to ping the hand and check for basic communication and motor telemetry:
```bash
python3 test_connection.py
```

### 4. Run Calibration & Safe Gesture Sequence
This script zeroes the hand (required before moving) and runs through coordinated patterns (Fist, Peace Sign, Thumbs Up, Pinch) step-by-step:
```bash
python3 test_gestures.py
```

### 5. Interactive Keyboard Controller
Control individual fingers and run pre-defined gestures in real-time using keyboard shortcuts:
```bash
python3 interactive_control.py
```

---

## 3. Byte-Level Communication Protocol

Communication with the eHand-6 uses **32-byte CAN FD frames** with **Bit Rate Switch (BRS)** enabled.

* **Right Hand CAN ID**: `0x11` (Default)
* **Left Hand CAN ID**: `0x12`

### Control Command Frame (PC ──► Hand)
The master commands the hand using a write frame or reads telemetry using a read frame:

| Byte Offset | Parameter Group | Byte Definition / Details |
| :---: | :--- | :--- |
| **Byte 0** | Command + ID | **Bits 0–1**: Command Type (`0x00` = Read, `0x01` = Write)<br>**Bits 2–7**: Motor Selection Bitmask (set bit to command motor 1–6) |
| **Byte 1** | Control Word | **Bits 0–3**: Control Mode (see modes table below)<br>**Bits 4–7**: Point number index (0–15) |
| **Bytes 2–6** | Thumb Horizontal | Position (1B) \| Speed (1B) \| Torque (1B) \| Reserved (2B) |
| **Bytes 7–11** | Thumb Vertical | Position (1B) \| Speed (1B) \| Torque (1B) \| Reserved (2B) |
| **Bytes 12–16** | Index Finger | Position (1B) \| Speed (1B) \| Torque (1B) \| Reserved (2B) |
| **Bytes 17–21** | Middle Finger | Position (1B) \| Speed (1B) \| Torque (1B) \| Reserved (2B) |
| **Bytes 22–26** | Ring Finger | Position (1B) \| Speed (1B) \| Torque (1B) \| Reserved (2B) |
| **Bytes 27–31** | Little Finger | Position (1B) \| Speed (1B) \| Torque (1B) \| Reserved (2B) |

### Control Modes (Byte 1)
| Mode Byte | Mode Name | Description |
| :---: | :--- | :--- |
| **0x00** | `DISABLED` | Emergency stop; cuts power to all motors immediately |
| **0x01** | `POSITION` | Standard closed-loop position control to target position |
| **0x02** | `FINGER_OPEN` | Opens the selected fingers using speed/torque parameters |
| **0x03** | `FINGER_CLOSE` | Closes the selected fingers using speed/torque parameters |
| **0x04** | `ZEROING` | Calibrates motor positions by homing to physical stall limit |
| **0x15** | `SAVE_POINT` | Saves current finger positions into point register 1 |
| **0x16** | `EXECUTE_POINT` | Moves all fingers to saved point register 1 |

---

## 4. Status Feedback Layout & Bitfield Decoding

When the hand receives a READ command, it replies with a 32-byte telemetry frame. 

Because the hand's internal MCU is **little-endian (ARM Cortex)**, structures containing bitfield variables are packed from **Least Significant Bit (LSB) to Most Significant Bit (MSB)**:

```
  Status/Fault Byte Layout (LSB-first):
  ┌───┬───┬───┬───┬───┬───┬───┬───┐
  │ F3│ F2│ F1│ F0│ S3│ S2│ S1│ S0│
  └───┴───┴───┴───┴───┴───┴───┴───┘
  ◄─── Fault ────► ◄─── State ───►
      (Bits 4-7)       (Bits 0-3)
```

To extract these values correctly in Python:
```python
state = status_byte & 0x0F          # Lower 4 bits
fault = (status_byte >> 4) & 0x0F   # Upper 4 bits
```

### Motor States (Lower 4 bits)
* `0x00` (Initializing): The MCU has powered up but has not completed zeroing.
* `0x01` (Standby): The motor/hand is ready to receive commands.
* `0x02` (Calibration): The motor is currently homing to discover physical limits.
* `0x03` (Position Mode): The motor is actively tracking target position.

### Fault Codes (Upper 4 bits)
* `0x00`: No fault (Safe state)
* `0x01`: Overcurrent protection triggered
* `0x02`: Overvoltage protection triggered
* `0x03`: Undervoltage protection triggered
* `0x04`: Overheat protection triggered
* `0x05`: Stall protection triggered
* `0x06`: Communication Timeout
* `0x07`: Hardware fault

---

## 5. File Structure

* **`ehand_driver.py`**: Main driver wrapper. Includes SocketCAN connection logic, binary frame construction, safety constraints, and bitfield parsing.
* **`test_connection.py`**: Quick link diagnostics that pings the hand and tests read/write capability.
* **`test_gestures.py`**: Runs through full safe test gesture cycles (open, close, ripple, peace,thumbs-up, pinch, fist).
* **`interactive_control.py`**: Full keyboard-controlled CLI dashboard showing real-time feedback.
* **`presentation_demo.py`**: A highly interactive demo script mapped to consecutive keyboard letters `a-p` to easily perform 16+ gestures (skipping the defective index finger).
* **`linkedin_demo.py`**: Coordinated 5-finger demo sequence (Waves, Claw Grasp, Thumbs-up, adapted Victory gesture) bypassing motor 3 (Index) to prevent noise if that finger has mechanical jams.
* **`troubleshoot_index.py`**: Targeted diagnostics tool for Motor 3 to determine mechanical stalls vs. sensor/electrical faults.
* **`monitor_index_manual.py`**: Real-time encoder feedback checker that keeps holding torque disabled so you can move a finger manually and test sensor integrity.
* **`setup_can.sh`**: One-command helper script that configures CAN FD interfaces correctly.

---

## 6. Troubleshooting

1. **"Failed to transmit: Network is down"**:
   * Bring up the CAN interface using `sudo ./setup_can.sh`. If it fails, make sure the USB-to-CAN adapter is plugged in and recognized (`lsusb`).
2. **No Response / Connection Timeout**:
   * Verify your 24V power supply is turned on and delivering power.
   * Make sure CAN_H and CAN_L are not swapped.
   * Verify termination jumper is on.
   * Ensure common ground connects the CANable and the 24V PSU.
3. **Firmware Compatibility**:
   * Standard MKS CANable candlelight firmware is CAN 2.0 only. If SocketCAN fails to enable the `fd on` flag, you must flash a CAN FD firmware (e.g. Elmue CANable V2.x firmware) onto your adapter.
