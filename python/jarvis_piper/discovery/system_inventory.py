"""
System Inventory Generator for JARVIS-PiPER.
Inspects hardware, ROS 2 distro, disk space, and generating docs/system_inventory.md.
"""

import os
import platform
import shutil
import subprocess
import sys
from typing import Dict, Any


def run_cmd(cmd: list) -> str:
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        return res.stdout.strip()
    except Exception:
        return "N/A"


def inspect_full_system() -> Dict[str, Any]:
    info = {
        "os": platform.system(),
        "release": platform.release(),
        "arch": platform.machine(),
        "python": sys.version.split()[0],
        "ros_distro": os.environ.get("ROS_DISTRO", "Not Sourced"),
        "ros2_path": shutil.which("ros2") or "Not found",
        "has_cuda": False,
        "gpu_name": "None",
        "disk_free_gb": round(shutil.disk_usage("/").free / (1024**3), 2),
    }

    # GPU check
    smi = shutil.which("nvidia-smi")
    if smi:
        gpu = run_cmd(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"])
        if gpu:
            info["has_cuda"] = True
            info["gpu_name"] = gpu

    return info


def write_inventory_doc(output_path: str = "docs/system_inventory.md"):
    data = inspect_full_system()
    content = f"""# System Inventory: JARVIS-PiPER

Generated on: {platform.node()}

## 1. Host & Compute Platform
- **Operating System**: {data['os']} ({data['release']})
- **Architecture**: {data['arch']}
- **Python Version**: {data['python']}
- **Available Disk Space**: {data['disk_free_gb']} GB

## 2. ROS 2 Environment
- **ROS_DISTRO**: {data['ros_distro']}
- **ROS 2 Executable**: {data['ros2_path']}

## 3. Acceleration & Compute
- **CUDA Detected**: {data['has_cuda']}
- **GPU Accelerator**: {data['gpu_name']}

## 4. Robot & Sensor Configuration
- **Robotic Arm**: AgileX PiPER 6-DOF
- **Teleoperator**: AgileX PIKA Sense 6-DoF Handheld
- **Gripper**: PIKA Parallel Linear Stroke Gripper (0-35mm)
"""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    return data
