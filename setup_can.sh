#!/bin/bash
# =============================================================================
# HITBOT eHand-6 CAN FD Interface Setup Script
# =============================================================================
# Sets up the SocketCAN interface for the MKS CANable V2.0 adapter
# with the exact parameters required by the eHand-6.
#
# Usage:
#   sudo ./setup_can.sh [interface_name]
#   sudo ./setup_can.sh can0       # default
#   sudo ./setup_can.sh can1       # if multiple adapters
#
# Requirements:
#   - Linux with SocketCAN support (kernel 5.x+)
#   - can-utils installed (sudo apt install can-utils)
#   - MKS CANable V2.0 with CAN FD firmware
# =============================================================================

set -e

IFACE="${1:-can0}"

echo "============================================"
echo "  eHand-6 CAN FD Interface Setup"
echo "============================================"
echo "  Interface: $IFACE"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "ERROR: This script must be run as root (use sudo)"
    exit 1
fi

# Check if can-utils is installed
if ! command -v candump &> /dev/null; then
    echo "Installing can-utils..."
    apt update && apt install -y can-utils
fi

# Check if interface exists
if ! ip link show "$IFACE" &> /dev/null; then
    echo "ERROR: Interface '$IFACE' not found!"
    echo ""
    echo "Troubleshooting:"
    echo "  1. Check USB connection: lsusb | grep -i can"
    echo "  2. Check kernel driver: dmesg | tail -20"
    echo "  3. If using candlelight firmware: should auto-create can0"
    echo "  4. If using slcan firmware: use slcand to create interface"
    echo ""
    echo "Available CAN interfaces:"
    ip link show type can 2>/dev/null || echo "  (none found)"
    exit 1
fi

# Bring down if already up
echo "  Bringing down $IFACE (if up)..."
ip link set "$IFACE" down 2>/dev/null || true

# Configure CAN FD with eHand-6 parameters
echo "  Configuring CAN FD parameters..."
echo "    Arbitration:  1 Mbps, 80% sample point"
echo "    Data phase:   5 Mbps, 75% sample point"
echo "    CAN FD:       enabled"

ip link set "$IFACE" up type can \
    bitrate 1000000 \
    sample-point 0.800 \
    dbitrate 5000000 \
    dsample-point 0.750 \
    fd on

# Check result
if [ $? -eq 0 ]; then
    echo ""
    echo "  ✓ Interface $IFACE is UP with CAN FD"
    echo ""
    echo "  Current configuration:"
    ip -details link show "$IFACE" | head -5
    echo ""
    echo "  Quick test commands:"
    echo "    candump $IFACE                    # Listen for traffic"
    echo "    python3 test_connection.py         # Test hand connection"
    echo ""
else
    echo ""
    echo "  ✗ FAILED to configure CAN FD!"
    echo ""
    echo "  This usually means the firmware does NOT support CAN FD."
    echo "  Solutions:"
    echo "    1. Flash Elmue CAN FD firmware for STM32G431"
    echo "       https://github.com/Elmue/CANable-2.5-firmware-Slcan-and-Candlelight"
    echo "    2. Use a different CAN FD adapter (e.g., PCAN-USB FD)"
    echo ""
    echo "  Falling back to CAN 2.0 (will NOT work with eHand-6):"
    echo "    ip link set $IFACE up type can bitrate 1000000"
    exit 1
fi
