# AgileX PiPER Arm: Hardware Setup & SocketCAN Configuration

> **MILESTONE 2 SAFETY NOTICE: ZERO PHYSICAL MOTION**  
> In Milestone 2, the PiPER manipulator is operated **strictly in read-only passive mode**. Under no circumstances should motor actuation frames (CAN ID `0x159`) or arbitrary `cansend` frames be transmitted. Motor enabling is strictly locked until Milestone 17 physical commissioning.

---

## 1. Hardware Specifications & Power

| Parameter | Specification | Notes |
| :--- | :--- | :--- |
| **Model** | AgileX PiPER 6-DOF Manipulator | S-V1.6-3 Firmware |
| **Payload** | 1.5 kg (rated) | Conservative safety limit: 1.0 kg |
| **Bus Interface** | CAN 2.0B / SocketCAN | Default bitrate: 1,000,000 bps (1 Mbps) |
| **Power Supply** | 24V DC / 10A regulated | Verify polarity before switching on |
| **CAN Adapter** | USB-to-CAN (e.g. Candlelight, CANable, gs_usb) | Connect to USB 3.0 port on NUC |

---

## 2. Wiring & Electrical Interconnect

1. **Power Connection**:
   - Connect the regulated 24V DC power supply to the PiPER base power port.
   - Ensure the emergency stop circuit is unlatched and functional.
   - Do **NOT** turn on main motor power until the CAN communication bus is verified.

2. **CAN Bus Topology**:
   - Connect CAN_H and CAN_L from the PiPER base DB9 or aviation plug to the USB-to-CAN adapter.
   - Verify that 120 $\Omega$ termination resistance is present across CAN_H and CAN_L when the system is unpowered.

---

## 3. Linux SocketCAN Interface Configuration

On the Ubuntu 22.04 LTS host (target NUC):

### A. Load Kernel Modules
```bash
sudo modprobe can
sudo modprobe can_raw
sudo modprobe can_dev
sudo modprobe gs_usb
```

### B. Bring Up Network Interface
Configure `can0` for standard 1 Mbps communication:
```bash
sudo ip link set can0 down 2>/dev/null || true
sudo ip link set can0 type can bitrate 1000000
sudo ip link set can0 txqueuelen 1000
sudo ip link set can0 up
```

### C. Verify Interface Status
```bash
ip -s -d link show can0
```
Expected output:
```text
can0: <NOARP,UP,LOWER_UP,ECHO> mtu 16 qdisc pfifo_fast state UP mode DEFAULT group default qlen 1000
    link/can  promiscuity 0 minmtu 0 maxmtu 0
    can state ERROR-ACTIVE (berr-counter tx 0 rx 0) restart-ms 0
          bitrate 1000000 sample-point 0.750
```

---

## 4. Read-Only Bring-up & Verification

Once the interface is `UP`, verify passive encoder telemetry without commanding the arm:

```bash
# Listen passively for 2 seconds (ZERO frames sent)
candump can0
```

### Expected Periodic Feedback CAN Frames:
The PiPER arm broadcasts periodic feedback frames from joints 1 through 6:
- Joint 1 Feedback: `0x2A1`
- Joint 2 Feedback: `0x2A2`
- Joint 3 Feedback: `0x2A3`
- Joint 4 Feedback: `0x2A4`
- Joint 5 Feedback: `0x2A5`
- Joint 6 Feedback: `0x2A6`

Each frame encodes 8 bytes containing 32-bit signed integer position (scaled at $0.001^\circ$ per count) and velocity.

---

## 5. Vendor ROS 2 Driver Hazard Mitigation

If using the vendor `piper_ros` workspace:
> [!CAUTION]
> The vendor launch file `~/piper_ros/src/piper/launch/start_single_piper.launch.py` defaults `auto_enable` to `true`.  
> Launching the vendor file directly will spontaneously power and enable motor coils!  
> Always pass `auto_enable:=false` or interface exclusively via the `jarvis` hardware abstraction layer (`jarvis.hardware.RealPiperArm`).
