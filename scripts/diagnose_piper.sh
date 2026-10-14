#!/usr/bin/env bash
# JARVIS-PiPER: PiPER Manipulator & CAN Diagnostics (Phase 3)
# STRICTLY PASSIVE / READ-ONLY: Never sends CAN frames, never enables motors.

set -e

echo "================================================================================"
echo "                 PIPER ARM & SOCKETCAN PASSIVE DIAGNOSTICS"
echo "================================================================================"

CAN_IF="${1:-can0}"

echo "[1/5] Checking Kernel SocketCAN Modules..."
if command -v lsmod &>/dev/null; then
    MODULES=$(lsmod | grep -E "^can|^can_raw|^can_dev|^gs_usb|^slcan" || true)
    if [ -n "$MODULES" ]; then
        echo "  [PASS] SocketCAN kernel modules loaded:"
        echo "$MODULES" | sed 's/^/    /'
    else
        echo "  [WARN] No standard SocketCAN modules visible in lsmod. (Check kernel support: modprobe can can_raw)"
    fi
else
    echo "  [INFO] lsmod not available."
fi

echo ""
echo "[2/5] Checking USB-to-CAN Hardware Enumeration..."
if command -v lsusb &>/dev/null; then
    USB_CAN=$(lsusb | grep -iE "can|candle|gs_usb|stm32|0483:5740|1d50:606f" || true)
    if [ -n "$USB_CAN" ]; then
        echo "  [PASS] USB CAN adapter detected:"
        echo "$USB_CAN" | sed 's/^/    /'
    else
        echo "  [WARN] No USB CAN adapter detected on USB bus. Ensure adapter is plugged into USB 3.0."
    fi
else
    echo "  [INFO] lsusb not available."
fi

echo ""
echo "[3/5] Checking Network Interface '$CAN_IF'..."
if command -v ip &>/dev/null; then
    if ip link show "$CAN_IF" &>/dev/null; then
        echo "  [PASS] Interface '$CAN_IF' is present."
        ip -s -d link show "$CAN_IF" | sed 's/^/    /'
        
        # Check if UP
        STATE=$(ip -br link show "$CAN_IF" | awk '{print $2}')
        if [ "$STATE" = "UP" ]; then
            echo "  [PASS] State is UP."
        else
            echo "  [WARN] State is $STATE (not UP). Bring up with:"
            echo "         sudo ip link set $CAN_IF up type can bitrate 1000000"
        fi
    else
        echo "  [WARN] Interface '$CAN_IF' does not exist."
        echo "         Plug in adapter and configure: sudo ip link set $CAN_IF up type can bitrate 1000000"
    fi
else
    echo "  [INFO] 'ip' command not found."
fi

echo ""
echo "[4/5] Inspecting Vendor Driver Repository..."
if [ -d "$HOME/piper_ros" ]; then
    echo "  [PASS] Found ~/piper_ros directory."
    LAUNCH_FILE="$HOME/piper_ros/src/piper/launch/start_single_piper.launch.py"
    if [ -f "$LAUNCH_FILE" ]; then
        echo "  [INFO] Launch file found: $LAUNCH_FILE"
        if grep -q "auto_enable.*default.*true" "$LAUNCH_FILE" 2>/dev/null; then
            echo "  [CAUTION] SAFETY HAZARD DETECTED in vendor launch file:"
            echo "            'auto_enable' defaults to TRUE. Spontaneous motor motion risk."
            echo "            Always launch through JARVIS safety supervisor or pass 'auto_enable:=false'."
        fi
    fi
else
    echo "  [INFO] ~/piper_ros not present on this machine (pure Python driver active)."
fi

echo ""
echo "[5/5] Read-Only Passive Telemetry Test..."
if command -v candump &>/dev/null && [ "$STATE" = "UP" ]; then
    echo "  [INFO] Passively listening for 2 seconds on $CAN_IF (ZERO packets sent)..."
    SNIFF=$(timeout 2 candump "$CAN_IF" 2>/dev/null | head -n 10 || true)
    if [ -n "$SNIFF" ]; then
        echo "  [PASS] CAN traffic detected on $CAN_IF:"
        echo "$SNIFF" | sed 's/^/    /'
    else
        echo "  [INFO] No CAN traffic received within 2s (arm unpowered or in standby)."
    fi
else
    echo "  [INFO] To passively monitor CAN telemetry traffic without commanding motors:"
    echo "         candump $CAN_IF"
fi
echo "================================================================================"
