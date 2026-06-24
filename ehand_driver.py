#!/usr/bin/env python3
"""
HITBOT eHand-6 CAN FD Driver
=============================
Core driver class for controlling the HITBOT eHand-6 dexterous hand
via CAN FD bus using python-can + SocketCAN.

Protocol source: eHand-6 Product Manual (20250808)
Communication: FDCAN, 32-byte frames
  - Arbitration: 1 Mbps, 80% sample point
  - Data phase:  5 Mbps, 75% sample point

Author: Robotics Integration Engineer
"""

import can
import time
import struct
from enum import IntEnum
from dataclasses import dataclass, field
from typing import Optional, List, Dict


# ============================================================================
# Constants from the official manual
# ============================================================================

class HandID(IntEnum):
    """CAN arbitration IDs for left/right hand."""
    RIGHT = 0x11
    LEFT  = 0x12


class ControlMode(IntEnum):
    """Control word mode selection (lower 4 bits of byte 2)."""
    DISABLED       = 0x00  # E-stop / disable all motors
    POSITION       = 0x01  # Move to target position/speed/torque
    FINGER_OPEN    = 0x02  # Open according to speed/torque
    FINGER_CLOSE   = 0x03  # Close according to speed/torque
    ZEROING        = 0x04  # Calibrate / zero the selected motors
    SAVE_POINT     = 0x05  # Save current positions to point N  (controlword = 0x15 for point 1)
    EXECUTE_POINT  = 0x06  # Execute saved point N              (controlword = 0x16 for point 1)


class CommandType(IntEnum):
    """Lower 2 bits of byte 1."""
    READ  = 0x00
    WRITE = 0x01


class MotorState(IntEnum):
    """State nibble values from status feedback."""
    INITIALIZING = 0x0
    STANDBY      = 0x1
    CALIBRATING  = 0x2
    POSITION_MODE = 0x3
    RESERVED_4   = 0x4
    AGING_MODE   = 0x5
    FAULT        = 0x6
    CMD_WAITING  = 0x7


class FaultCode(IntEnum):
    """Fault code nibble values from status feedback."""
    NONE             = 0x0
    OVERCURRENT      = 0x1
    OVERVOLTAGE      = 0x2
    UNDERVOLTAGE     = 0x3
    OVERHEAT         = 0x4
    STALL            = 0x5
    COMM_TIMEOUT     = 0x6
    HARDWARE_FAULT   = 0x7


# Motor/finger names for display
MOTOR_NAMES = {
    1: "Thumb Horizontal",
    2: "Thumb Vertical",
    3: "Index Finger",
    4: "Middle Finger",
    5: "Ring Finger",
    6: "Little Finger",
}

# All motors bitmask (bits 2-7 set = 0b11111100 = 0xFC for upper 6 bits)
ALL_MOTORS_MASK = 0x3F  # This is shifted left by 2 to form the byte


# ============================================================================
# Data structures
# ============================================================================

@dataclass
class FingerParams:
    """Control parameters for a single finger/motor."""
    position: int = 0x80   # 0-255, 0x80 = 50% center
    speed: int    = 0x80   # 0-255, 0x80 = 50% speed
    torque: int   = 0xCC   # 0-255, 0xCC = 80% torque

    def __post_init__(self):
        self.position = max(0, min(255, self.position))
        self.speed    = max(0, min(255, self.speed))
        self.torque   = max(0, min(255, self.torque))


@dataclass
class FingerStatus:
    """Status feedback for a single finger/motor."""
    state: MotorState = MotorState.INITIALIZING
    fault: FaultCode  = FaultCode.NONE
    position: int     = 0
    speed: int        = 0
    # Target values (only populated when parsed from a write response echo frame)
    target_position: Optional[int] = None
    target_speed: Optional[int] = None
    target_torque: Optional[int] = None

    @property
    def state_name(self) -> str:
        try:
            return MotorState(self.state).name
        except ValueError:
            return f"UNKNOWN(0x{self.state:X})"

    @property
    def fault_name(self) -> str:
        try:
            return FaultCode(self.fault).name
        except ValueError:
            return f"UNKNOWN(0x{self.fault:X})"

    @property
    def position_pct(self) -> float:
        return (self.position / 255.0) * 100.0

    @property
    def speed_pct(self) -> float:
        return (self.speed / 255.0) * 100.0


@dataclass
class HandStatus:
    """Complete status of the hand."""
    machine_state: int = 0
    machine_fault: int = 0
    is_write_response: bool = False
    fingers: Dict[str, FingerStatus] = field(default_factory=dict)
    raw_data: bytes = b''
    timestamp: float = 0.0

    @property
    def machine_state_name(self) -> str:
        states = {
            0x00: "INITIALIZING",
            0x01: "STANDBY",
            0x02: "CALIBRATION",  # zeroing / zero state
            0x03: "POSITION_MODE",
            0x05: "AGING_MODE",
            0x06: "FAULT",
            0x07: "CMD_WAITING",
        }
        return states.get(self.machine_state, f"UNKNOWN(0x{self.machine_state:02X})")

    @property
    def machine_fault_name(self) -> str:
        faults = {
            0x0: "NONE",
            0x1: "OVERCURRENT",
            0x2: "OVERVOLTAGE",
            0x3: "UNDERVOLTAGE",
            0x4: "OVERHEAT",
            0x5: "STALL",
            0x6: "COMM_TIMEOUT",
            0x7: "HARDWARE_FAULT",
        }
        return faults.get(self.machine_fault, f"UNKNOWN(0x{self.machine_fault:02X})")


# ============================================================================
# Driver class
# ============================================================================

class EHand6Driver:
    """
    Driver for HITBOT eHand-6 dexterous hand via CAN FD.

    Usage:
        driver = EHand6Driver(channel='can0', hand_id=HandID.RIGHT)
        driver.connect()

        # Read status
        status = driver.read_status()
        print(status)

        # Move all fingers to center
        driver.set_all_fingers(position=0x80, speed=0x80, torque=0xCC)

        # Open hand
        driver.open_hand()

        # Close hand
        driver.close_hand()

        # Zero/calibrate
        driver.zero_hand()

        # Emergency stop
        driver.emergency_stop()

        driver.disconnect()
    """

    FRAME_SIZE = 32  # 32-byte CAN FD frame

    def __init__(
        self,
        channel: str = 'can0',
        hand_id: int = HandID.RIGHT,
        bustype: str = 'socketcan',
        timeout: float = 1.0,
    ):
        self.channel = channel
        self.hand_id = hand_id
        self.bustype = bustype
        self.timeout = timeout
        self.bus: Optional[can.Bus] = None

    # ---- Connection ----

    def connect(self):
        """Open the CAN bus connection."""
        self.bus = can.interface.Bus(
            channel=self.channel,
            interface=self.bustype,
            fd=True,  # Enable CAN FD
        )
        print(f"[eHand6] Connected to {self.channel} (CAN FD)")
        print(f"[eHand6] Hand ID: 0x{self.hand_id:02X} "
              f"({'RIGHT' if self.hand_id == HandID.RIGHT else 'LEFT'})")

    def disconnect(self):
        """Close the CAN bus connection."""
        if self.bus:
            self.bus.shutdown()
            self.bus = None
            print("[eHand6] Disconnected")

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.disconnect()

    # ---- Frame construction ----

    def _build_command_byte(
        self, cmd_type: CommandType, motor_ids: Optional[List[int]] = None
    ) -> int:
        """
        Build byte 1: Command + Motor ID selection.

        Lower 2 bits = command type (read/write)
        Upper 6 bits = motor selection (bits 2-7 correspond to motors 1-6)

        motor_ids: list of motor numbers (1-6), or None for all motors.
        """
        if motor_ids is None:
            # Select all motors: bits 2-7 all set = 0b11111100
            motor_mask = ALL_MOTORS_MASK
        else:
            motor_mask = 0
            for mid in motor_ids:
                if 1 <= mid <= 6:
                    motor_mask |= (1 << (mid - 1))  # bit 0-5 in the mask
                else:
                    raise ValueError(f"Motor ID must be 1-6, got {mid}")

        # Shift motor mask to upper 6 bits (bits 2-7) and OR with command
        return (motor_mask << 2) | (cmd_type & 0x03)

    def _build_control_word(self, mode: ControlMode, point_num: int = 0) -> int:
        """
        Build byte 2: Control word.

        Lower 4 bits = mode
        Upper 4 bits = point number (0-15)

        Special cases from manual:
          0x15 = save point 1 (mode=5, point=1)
          0x16 = execute point 1 (mode=6, point=1)
        """
        if mode == ControlMode.SAVE_POINT:
            return 0x15  # As per manual example
        elif mode == ControlMode.EXECUTE_POINT:
            return 0x16  # As per manual example
        else:
            return ((point_num & 0x0F) << 4) | (mode & 0x0F)

    def _build_control_frame(
        self,
        mode: ControlMode,
        fingers: Optional[Dict[int, FingerParams]] = None,
        motor_ids: Optional[List[int]] = None,
        point_num: int = 0,
    ) -> bytes:
        """
        Build a complete 32-byte control command frame.

        fingers: dict mapping motor_id (1-6) to FingerParams.
                 If None, zeros are used for all finger data.
        motor_ids: which motors to select. None = all.
        """
        data = bytearray(self.FRAME_SIZE)

        # Byte 1: Command + ID
        data[0] = self._build_command_byte(CommandType.WRITE, motor_ids)

        # Byte 2: Control word
        data[1] = self._build_control_word(mode, point_num)

        # Bytes 3-32: 6 groups × 5 bytes (position, speed, torque, reserved, reserved)
        if fingers:
            for motor_id in range(1, 7):
                offset = 2 + (motor_id - 1) * 5  # Each group is 5 bytes
                params = fingers.get(motor_id, FingerParams(0, 0, 0))
                data[offset]     = params.position
                data[offset + 1] = params.speed
                data[offset + 2] = params.torque
                data[offset + 3] = 0x00  # Reserved
                data[offset + 4] = 0x00  # Reserved

        return bytes(data)

    def _build_read_frame(self) -> bytes:
        """
        Build a 32-byte read-status command frame.
        Only byte 1 needs to be filled (read + all motors).
        """
        data = bytearray(self.FRAME_SIZE)
        # FC = 0b11111100 = all motors selected + read command (bits 0-1 = 00)
        data[0] = self._build_command_byte(CommandType.READ)
        return bytes(data)

    # ---- Sending ----

    def _send_frame(self, data: bytes) -> None:
        """Send a CAN FD frame to the hand."""
        if not self.bus:
            raise RuntimeError("Not connected. Call connect() first.")

        msg = can.Message(
            arbitration_id=self.hand_id,
            data=data,
            is_fd=True,
            bitrate_switch=True,  # Use 5 Mbps for data phase
            is_extended_id=False,
        )
        try:
            self.bus.send(msg)
        except can.CanError as e:
            print(f"[eHand6] ERROR sending frame: {e}")
            raise

    def _receive_frame(self, timeout: Optional[float] = None) -> Optional[can.Message]:
        """
        Receive a CAN FD frame from the hand.
        Returns None if timeout expires.
        """
        if not self.bus:
            raise RuntimeError("Not connected. Call connect() first.")

        t = timeout if timeout is not None else self.timeout
        msg = self.bus.recv(timeout=t)
        return msg

    # ---- High-level commands ----

    def read_status(self) -> Optional[HandStatus]:
        """
        Send read command and parse the status feedback frame.
        Returns HandStatus or None if no response.
        """
        self._send_frame(self._build_read_frame())

        msg = self._receive_frame()
        if msg is None:
            print("[eHand6] WARNING: No response to status read")
            return None

        return self._parse_status(msg)

    def set_all_fingers(
        self,
        position: int = 0x80,
        speed: int = 0x80,
        torque: int = 0xCC,
    ) -> Optional[HandStatus]:
        """
        Set all fingers to the same position/speed/torque.

        Args:
            position: 0-255 (0=fully open, 255=fully closed, 128=center)
            speed: 0-255 (0=slowest, 255=fastest, 128=50%)
            torque: 0-255 (0=min, 255=max, 204=80%)
        """
        params = FingerParams(position, speed, torque)
        fingers = {i: params for i in range(1, 7)}

        data = self._build_control_frame(
            mode=ControlMode.POSITION,
            fingers=fingers,
        )
        self._send_frame(data)

        # Read response
        msg = self._receive_frame()
        if msg:
            return self._parse_status(msg)
        return None

    def set_finger(
        self,
        motor_id: int,
        position: int = 0x80,
        speed: int = 0x80,
        torque: int = 0xCC,
    ) -> Optional[HandStatus]:
        """
        Set a single finger to target position.

        Args:
            motor_id: 1-6 (see MOTOR_NAMES)
            position: 0-255
            speed: 0-255
            torque: 0-255
        """
        params = FingerParams(position, speed, torque)
        fingers = {motor_id: params}

        data = self._build_control_frame(
            mode=ControlMode.POSITION,
            fingers=fingers,
            motor_ids=[motor_id],
        )
        self._send_frame(data)

        msg = self._receive_frame()
        if msg:
            return self._parse_status(msg)
        return None

    def open_hand(self, speed: int = 0x80, torque: int = 0xCC) -> Optional[HandStatus]:
        """
        Open all fingers using FINGER_OPEN mode.
        In this mode, only speed and torque matter (no position).
        """
        params = FingerParams(0, speed, torque)
        fingers = {i: params for i in range(1, 7)}

        data = self._build_control_frame(
            mode=ControlMode.FINGER_OPEN,
            fingers=fingers,
        )
        self._send_frame(data)

        msg = self._receive_frame()
        if msg:
            return self._parse_status(msg)
        return None

    def close_hand(self, speed: int = 0x80, torque: int = 0xCC) -> Optional[HandStatus]:
        """
        Close all fingers using FINGER_CLOSE mode.
        In this mode, only speed and torque matter (no position).
        """
        params = FingerParams(0, speed, torque)
        fingers = {i: params for i in range(1, 7)}

        data = self._build_control_frame(
            mode=ControlMode.FINGER_CLOSE,
            fingers=fingers,
        )
        self._send_frame(data)

        msg = self._receive_frame()
        if msg:
            return self._parse_status(msg)
        return None

    def zero_hand(self) -> Optional[HandStatus]:
        """
        Zero/calibrate all fingers.
        Motors will move to their zero reference position.
        """
        data = self._build_control_frame(mode=ControlMode.ZEROING)
        self._send_frame(data)

        msg = self._receive_frame(timeout=5.0)  # Zeroing takes longer
        if msg:
            return self._parse_status(msg)
        return None

    def emergency_stop(self) -> None:
        """
        Emergency stop — disable all motors immediately.
        Does NOT wait for response.
        """
        data = self._build_control_frame(mode=ControlMode.DISABLED)
        self._send_frame(data)
        print("[eHand6] *** EMERGENCY STOP SENT ***")

    def save_point(self, point_num: int = 1) -> Optional[HandStatus]:
        """Save current positions to a point number (0-15)."""
        data = self._build_control_frame(
            mode=ControlMode.SAVE_POINT,
            point_num=point_num,
        )
        self._send_frame(data)

        msg = self._receive_frame()
        if msg:
            return self._parse_status(msg)
        return None

    def execute_point(self, point_num: int = 1) -> Optional[HandStatus]:
        """Execute a previously saved point."""
        data = self._build_control_frame(
            mode=ControlMode.EXECUTE_POINT,
            point_num=point_num,
        )
        self._send_frame(data)

        msg = self._receive_frame()
        if msg:
            return self._parse_status(msg)
        return None

    # ---- Status parsing ----

    def _parse_status(self, msg: can.Message) -> HandStatus:
        """
        Parse a 32-byte status feedback frame from the hand.

        Feedback layout (from manual section 4/5.2):
          Byte 1:  Response type + motor ID bits
          Byte 2:  Machine state & fault (if read) or control word (if write)
          Bytes 3-7:   Thumb horizontal (state+fault, position, speed, rsv, rsv)
          Bytes 8-12:  Thumb vertical
          Bytes 13-17: Index finger
          Bytes 18-22: Middle finger
          Bytes 23-27: Ring finger
          Bytes 28-32: Little finger
        """
        data = msg.data
        status = HandStatus(
            raw_data=bytes(data),
            timestamp=msg.timestamp or time.time(),
        )

        if len(data) < 32:
            print(f"[eHand6] WARNING: Short frame ({len(data)} bytes, expected 32)")
            status.machine_state = data[1] if len(data) > 1 else 0
            return status

        # Check if this is a write response (cmd_type = 3)
        cmd_type = data[0] & 0x03
        if cmd_type == 0x03:
            status.is_write_response = True

        # Byte 2: state + fault for read, control word for write
        state_fault_byte = data[1]
        if not status.is_write_response:
            status.machine_state = state_fault_byte & 0x0F
            status.machine_fault = (state_fault_byte >> 4) & 0x0F
        else:
            status.machine_state = state_fault_byte
            status.machine_fault = 0

        # Parse each finger (6 groups of 5 bytes starting at byte 3)
        finger_names = [
            "Thumb Horizontal",
            "Thumb Vertical",
            "Index Finger",
            "Middle Finger",
            "Ring Finger",
            "Little Finger",
        ]

        for i, name in enumerate(finger_names):
            offset = 2 + i * 5

            if not status.is_write_response:
                state_fault = data[offset]
                state = state_fault & 0x0F          # Lower nibble = state (LSB bitfield)
                fault = (state_fault >> 4) & 0x0F   # Upper nibble = fault (MSB bitfield)

                position = data[offset + 1]
                speed    = data[offset + 2]

                status.fingers[name] = FingerStatus(
                    state=MotorState(state) if state in MotorState._value2member_map_ else state,
                    fault=FaultCode(fault) if fault in FaultCode._value2member_map_ else fault,
                    position=position,
                    speed=speed,
                )
            else:
                # Write response contains target values (position, speed, torque)
                target_pos = data[offset]
                target_spd = data[offset + 1]
                target_trq = data[offset + 2]
                status.fingers[name] = FingerStatus(
                    target_position=target_pos,
                    target_speed=target_spd,
                    target_torque=target_trq,
                )

        return status

    # ---- Display helpers ----

    @staticmethod
    def print_status(status: HandStatus) -> None:
        """Pretty-print hand status."""
        if status is None:
            print("[eHand6] No status available")
            return

        print("\n" + "=" * 60)
        if status.is_write_response:
            print(f"  eHand-6 Write Response Echo (Targets)")
            print(f"  Control Word: 0x{status.machine_state:02X}")
        else:
            print(f"  eHand-6 Status Report")
            print(f"  Machine State: {status.machine_state_name}")
            if status.machine_fault != 0:
                print(f"  Machine Fault: {status.machine_fault_name}")
        print("=" * 60)

        for name, fs in status.fingers.items():
            if status.is_write_response:
                print(
                    f"  {name:20s} | "
                    f"Tar Pos: {fs.target_position:3d} | "
                    f"Tar Spd: {fs.target_speed:3d} | "
                    f"Tar Trq: {fs.target_torque:3d}"
                )
            else:
                fault_str = f" ⚠ FAULT: {fs.fault_name}" if fs.fault != FaultCode.NONE else ""
                print(
                    f"  {name:20s} | "
                    f"State: {fs.state_name:15s} | "
                    f"Pos: {fs.position_pct:5.1f}% ({fs.position:3d}) | "
                    f"Spd: {fs.speed_pct:5.1f}%"
                    f"{fault_str}"
                )

        print("=" * 60)
        print(f"  Raw: {status.raw_data.hex(' ')}")
        print()


# ============================================================================
# Quick self-test
# ============================================================================

if __name__ == "__main__":
    print("eHand-6 Driver Module")
    print("=" * 40)
    print("This module provides the EHand6Driver class.")
    print("Run test_connection.py or test_gestures.py for testing.")
    print()

    # Demo: show frame construction without sending
    driver = EHand6Driver.__new__(EHand6Driver)
    driver.hand_id = HandID.RIGHT

    # Build example frames
    print("Example frames (hex):")
    print()

    # Read status
    read_frame = driver._build_read_frame()
    print(f"  Read all status:   {read_frame.hex(' ')}")

    # Position mode, all fingers center, 50% speed, 80% torque
    center_params = FingerParams(0x80, 0x80, 0xCC)
    center_fingers = {i: center_params for i in range(1, 7)}
    pos_frame = driver._build_control_frame(ControlMode.POSITION, center_fingers)
    print(f"  Position (center): {pos_frame.hex(' ')}")

    # Open hand
    open_frame = driver._build_control_frame(ControlMode.FINGER_OPEN, center_fingers)
    print(f"  Open hand:         {open_frame.hex(' ')}")

    # Close hand
    close_frame = driver._build_control_frame(ControlMode.FINGER_CLOSE, center_fingers)
    print(f"  Close hand:        {close_frame.hex(' ')}")

    # Zero
    zero_frame = driver._build_control_frame(ControlMode.ZEROING)
    print(f"  Zero hand:         {zero_frame.hex(' ')}")

    # E-stop
    stop_frame = driver._build_control_frame(ControlMode.DISABLED)
    print(f"  Emergency stop:    {stop_frame.hex(' ')}")

    # Verify against manual example
    print()
    print("Manual example verification:")
    print(f"  Manual TX: fd 01 80 ff ff 00 00 33 cc e6 00 00 4d c0 b3 00 00 66 d9 f3 00 00 99 a6 8d 00 00 5f 76 8d 00 00")
    manual_fingers = {
        1: FingerParams(0x80, 0xFF, 0xFF),   # Thumb horiz: pos=50%, spd=100%, trq=100%
        2: FingerParams(0x33, 0xCC, 0xE6),   # Thumb vert: pos=20%, spd=80%, trq=90%
        3: FingerParams(0x4D, 0xC0, 0xB3),   # Index: pos=30%, spd=75%, trq=70%
        4: FingerParams(0x66, 0xD9, 0xF3),   # Middle: pos=40%, spd=85%, trq=95%
        5: FingerParams(0x99, 0xA6, 0x8D),   # Ring: pos=60%, spd=65%, trq=55%  (manual says ~60%)
        6: FingerParams(0x5F, 0x76, 0x8D),   # Little: pos=37%, spd=46%, trq=55%
    }
    verify_frame = driver._build_control_frame(ControlMode.POSITION, manual_fingers)
    print(f"  Our build: {verify_frame.hex(' ')}")
    match = verify_frame.hex(' ') == "fd 01 80 ff ff 00 00 33 cc e6 00 00 4d c0 b3 00 00 66 d9 f3 00 00 99 a6 8d 00 00 5f 76 8d 00 00"
    print(f"  Match: {'✓ PASS' if match else '✗ FAIL'}")
