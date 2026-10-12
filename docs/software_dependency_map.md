# JARVIS-PiPER: Software Dependency & Interface Map

**Architecture:** Layered Robotics & Embodied AI Architecture  
**ROS 2 Distributions:** ROS 2 Lyrical (WSL Ubuntu 26.04) & ROS 2 Humble (WSL Ubuntu 22.04)  
**Python Ecosystem:** Python 3.11.9 / 3.10.12 with PyTorch 2.x, ONNX Runtime, Ultralytics YOLO

---

## 1. System Architecture Map

```mermaid
graph TD
    subgraph UI ["Human Interaction & Task Interface"]
        VoiceText["Natural Language Instruction\n('Pick up red block and place in bowl')"]
        JARVIS["JARVIS Conversational Orchestrator\n(python/jarvis_piper/agent/)"]
    end

    subgraph Perception ["Perception & World State"]
        Camera["RealSense D435 / D455\n(/camera/color/image_raw)"]
        YOLO["YOLO11 Object Detector\n(yolo11n.pt: ['bowl', 'cup', 'red block'])"]
        WorldModel["World Model & Centroid Estimation\n(3D Coordinates in robot frame)"]
    end

    subgraph Planning ["Task & Motion Planning"]
        TaskPlan["21-Step Parameterized Pipeline\n(python/jarvis_piper/tasks/pick_and_place.py)"]
        Kinematics["Piper 6-DOF Kinematics & DLS IK\n(python/world_model/spatial.py)"]
        MoveIt2["MoveIt 2 Trajectory Planning\n(ranger_manipulation/ranger_piper.srdf)"]
    end

    subgraph SafetyLayer ["Independent Safety Supervisor"]
        Safety["Safety Supervisor (Hard Interlocks)\n- Joint Limits Enforced\n- Velocity Capped to 1.5 rad/s\n- Workspace Bounding Box\n- Dead-man E-Stop Latch"]
    end

    subgraph Execution ["Hardware & Simulation Adapters"]
        RealArm["Piper 1 Real Adapter\n(SocketCAN 1 Mbps / can0)"]
        SimArm["Simulation / Headless Articulation\n(Isaac Sim / PhysX / Gazebo)"]
        GripperCtrl["Parallel Gripper Controller\n(Stroke 0 to 0.035 m)"]
    end

    subgraph DataEngine ["Data Collection & MLOps"]
        Sync["Multimodal Ring Buffer & Sync"]
        Journal["stream_journal.jsonl & MCAP"]
        Exporters["Universal Exporter\n- LeRobot v2.0\n- ALOHA HDF5\n- RLDS Open-X"]
    end

    VoiceText --> JARVIS
    JARVIS --> TaskPlan
    Camera --> YOLO
    YOLO --> WorldModel
    WorldModel --> TaskPlan
    TaskPlan --> Kinematics
    TaskPlan --> MoveIt2
    Kinematics --> Safety
    MoveIt2 --> Safety
    Safety --> RealArm
    Safety --> SimArm
    Safety --> GripperCtrl
    RealArm --> Sync
    SimArm --> Sync
    Camera --> Sync
    Sync --> Journal
    Journal --> Exporters
```

---

## 2. Software Component Mapping

| Subsystem | Source Location | Dependencies | Primary ROS Topics / Services |
| :--- | :--- | :--- | :--- |
| **Agent / Orchestrator** | `python/jarvis_piper/agent/` | Regex, PyYAML | `/jarvis/instruction` |
| **Object Detection** | `Jarvis_Object_Detection.v1i.yolov11` | `ultralytics`, OpenCV, PyTorch | `/perception/detections` |
| **Spatial Kinematics** | `python/world_model/spatial.py` | NumPy, SciPy | Algorithmic FK/IK/Jacobian |
| **Safety Supervisor** | `python/jarvis_piper/safety/supervisor.py` | NumPy | State validation & E-stop |
| **Task Execution** | `python/jarvis_piper/tasks/pick_and_place.py` | Python 3.11 | High-level state machine |
| **MoveIt 2 Planning** | `ranger_manipulation/config/ranger_piper.srdf` | MoveIt 2, OMPL | `/piper_arm_controller/follow_joint_trajectory` |
| **Gripper Controller** | `ranger_control/config/controller.yaml` | ros2_control | `/piper_gripper_controller/follow_joint_trajectory` |
| **Data Exporter** | `python/dataset/exporters.py` | `h5py`, NumPy, OpenCV | LeRobot v2.0, ALOHA HDF5, RLDS |
| **Isaac Sim Articulation** | `scripts/isaac/` | Isaac Sim 4.x / Isaac Lab | `models/usd/piper.usda` |

---

## 3. Python Package Environment

The following key packages are verified and available:
- `torch>=2.1.0` (with CUDA support on RTX 5060)
- `onnx>=1.23.2` & `onnxruntime>=1.31.0`
- `opencv-python>=4.8.0`
- `numpy>=1.22.0`
- `pytest>=8.0.0`
- `h5py>=3.8.0`
- `pyyaml>=6.0`
