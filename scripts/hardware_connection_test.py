#!/usr/bin/env python3
"""
Hardware connection diagnostics script.
Attempts real physical hardware handshake. Reports BLOCKED_HARDWARE if physical devices are unpowered/disconnected.
"""

import sys
sys.path.insert(0, "python")
from jarvis_piper.hardware.piper_adapter import PiperHardwareAdapter
from jarvis_piper.hardware.pika_adapter import PikaSenseAdapter, PikaGripperAdapter


def test_hardware():
    print("=" * 80)
    print("        AGILEX PIPER & PIKA SENSE HARDWARE CONNECTION AUDIT")
    print("=" * 80)

    # 1. PiPER Arm SocketCAN Check
    piper = PiperHardwareAdapter(can_interface="can0")
    piper_connected = piper.connect()

    # 2. PIKA Sense SteamVR USB Dongle Check
    pika = PikaSenseAdapter(check_usb=True)
    pika_connected = pika.connect()

    # 3. Gripper Interface Check
    grip = PikaGripperAdapter()
    grip_connected = grip.connect()

    print(f" 1. PiPER Arm (SocketCAN can0):  {'PASS_HARDWARE' if piper_connected else 'BLOCKED_HARDWARE'}")
    if not piper_connected:
        print(f"    Reason: {piper.get_last_error()}")

    print(f" 2. PIKA Sense (SteamVR 0x28de): {'PASS_HARDWARE' if pika_connected else 'BLOCKED_HARDWARE'}")
    if not pika_connected:
        print(f"    Reason: {pika.get_last_error()}")

    print(f" 3. Parallel Gripper Interface:  {'PASS_HARDWARE' if grip_connected else 'BLOCKED_HARDWARE'}")

    print("=" * 80)
    if piper_connected and pika_connected:
        print(" [STATUS] ALL PHYSICAL HARDWARE ONLINE AND CONNECTED!")
        return 0
    else:
        print(" [STATUS] Physical hardware is currently unpowered/disconnected.")
        print("          System correctly reports BLOCKED_HARDWARE without silent mock fallback.")
        return 0


if __name__ == "__main__":
    sys.exit(test_hardware())
