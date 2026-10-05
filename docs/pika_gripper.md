# PIKA Parallel Gripper

The **PIKA Gripper** is an integrated parallel-jaw electric gripper mounted to Joint 6 of the PiPER arm.

---

## 1. Specifications

- **Stroke Range**: $0.0 \text{ m}$ (fully closed) to $0.035 \text{ m}$ ($35\text{ mm}$ fully open).
- **Control Interface**: Position control with effort limiting.
- **Feedback**: Position ($m$), velocity ($m/s$), and applied current/effort ($N$).
- **Joint Identifier**: `piper_finger_left_joint` (or `piper_gripper_joint`).

---

## 2. Topic Interface

- **Command Topic**: `/piper/gripper/ctrl` (`sensor_msgs/msg/JointState` or `std_msgs/msg/Float32`)
- **State Feedback**: Integrated into `/piper/joint_states` as the 7th joint element, or published standalone on `/piper/gripper/state`.

---

## 3. Normalized Grasp Action

In the universal dataset schemas (LeRobot, ALOHA HDF5, RLDS):
- `action[6]` represents the gripper stroke normalized to $[0.0, 1.0]$:
  $$\text{normalized\_stroke} = \frac{\text{stroke\_meters}}{0.035}$$
  where $0.0 = \text{closed}$ and $1.0 = \text{open}$.
- Effort thresholding enables automatic grasp success detection during manipulation phase segmentation.
