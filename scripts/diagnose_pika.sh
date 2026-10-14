#!/usr/bin/env bash
# JARVIS-PiPER: PIKA Sense & Tracking Diagnostics (Phase 4)
# STRICTLY PASSIVE / READ-ONLY: Audits USB, udev, and libsurvive state without modification.

set -e

echo "================================================================================"
echo "                 PIKA SENSE & OPTICAL TRACKING PASSIVE DIAGNOSTICS"
echo "================================================================================"

echo "[1/5] Checking SteamVR Wireless Receiver USB Dongle..."
if command -v lsusb &>/dev/null; then
    VIVE_USB=$(lsusb | grep -iE "28de:|valve|steam|htc" || true)
    if [ -n "$VIVE_USB" ]; then
        echo "  [PASS] SteamVR receiver dongle detected:"
        echo "$VIVE_USB" | sed 's/^/    /'
    else
        echo "  [WARN] SteamVR wireless dongle (VID 0x28de) not detected on USB bus."
        echo "         Plug in the wireless dongle to establish optical tracking connection."
    fi
else
    echo "  [INFO] lsusb command not available."
fi

echo ""
echo "[2/5] Checking Serial Port Devices (/dev/ttyACM*, /dev/ttyUSB*)..."
SERIALS=$(ls -la /dev/ttyACM* /dev/ttyUSB* 2>/dev/null || true)
if [ -n "$SERIALS" ]; then
    echo "  [PASS] Active serial interfaces:"
    echo "$SERIALS" | sed 's/^/    /'
else
    echo "  [INFO] No active /dev/ttyACM* or /dev/ttyUSB* devices detected."
fi

echo ""
echo "[3/5] Auditing Linux User Group Permissions..."
USER_GROUPS=$(groups 2>/dev/null || id -Gn 2>/dev/null || true)
echo "  Current user groups: $USER_GROUPS"
if echo "$USER_GROUPS" | grep -q "dialout"; then
    echo "  [PASS] User is a member of 'dialout' (serial port access permitted)."
else
    echo "  [WARN] User is NOT in 'dialout' group. Add user with: sudo usermod -aG dialout \$USER"
fi
if echo "$USER_GROUPS" | grep -q "plugdev"; then
    echo "  [PASS] User is a member of 'plugdev' (USB device access permitted)."
else
    echo "  [INFO] User is not in 'plugdev' group."
fi

echo ""
echo "[4/5] Checking udev Rules for SteamVR Dongle..."
UDEV_VIVE=$(find /etc/udev/rules.d/ /lib/udev/rules.d/ -name "*vive*.rules" -o -name "*pika*.rules" 2>/dev/null || true)
if [ -n "$UDEV_VIVE" ]; then
    echo "  [PASS] Tracking udev rules detected:"
    echo "$UDEV_VIVE" | sed 's/^/    /'
else
    echo "  [WARN] No SteamVR / Vive udev rules found in /etc/udev/rules.d/."
    echo "         Run './install.sh --system' to configure non-destructive USB permissions."
fi

echo ""
echo "[5/5] Checking libsurvive Optical Calibration Status..."
SURVIVE_CONF="$HOME/.config/libsurvive/config.json"
if [ -f "$SURVIVE_CONF" ]; then
    echo "  [PASS] Found libsurvive configuration: $SURVIVE_CONF"
    if grep -q "Lighthouse" "$SURVIVE_CONF" 2>/dev/null; then
        echo "  [PASS] Calibration matrix contains calibrated Lighthouse entries."
    else
        echo "  [WARN] config.json exists but lacks calibrated base station geometry."
    fi
else
    echo "  [INFO] No ~/.config/libsurvive/config.json found. System status: UNCALIBRATED."
    echo "         Lighthouse spatial calibration will be required prior to teleoperation."
fi

echo "================================================================================"
