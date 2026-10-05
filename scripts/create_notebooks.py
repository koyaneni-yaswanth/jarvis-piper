"""
Helper script to generate the 5 research Jupyter Notebooks.
"""

import json
from pathlib import Path

notebooks_dir = Path("notebooks")
notebooks_dir.mkdir(parents=True, exist_ok=True)

def create_nb(filename, title, cells_data):
    cells = []
    for c_type, content in cells_data:
        if c_type == "markdown":
            cells.append({
                "cell_type": "markdown",
                "metadata": {},
                "source": [line + "\n" for line in content.split("\n")]
            })
        elif c_type == "code":
            cells.append({
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [line + "\n" for line in content.split("\n")]
            })
    nb = {
        "cells": cells,
        "metadata": {
            "language_info": {"name": "python", "version": "3.10"}
        },
        "nbformat": 4,
        "nbformat_minor": 2
    }
    with open(notebooks_dir / filename, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1)
    print(f"Created {filename}")

# 1. dataset_inspection.ipynb
create_nb(
    "dataset_inspection.ipynb",
    "Dataset Inspection & Provenance",
    [
        ("markdown", "# JARVIS-PiPER :: Dataset Inspection & Metadata Provenance\nThis notebook demonstrates loading, inspecting, and validating recorded demonstration episodes."),
        ("code", "import os\nimport sys\nimport json\nfrom pathlib import Path\nimport matplotlib.pyplot as plt\n\n# Add python package to sys.path\nsys.path.insert(0, str(Path.cwd().parent / 'python'))\nfrom dataset.reader import EpisodeReader\nfrom dataset.quality import QualityScorer\nprint('Imports successful!')"),
        ("code", "raw_dir = Path('../dataset/raw')\nepisodes = sorted([p for p in raw_dir.iterdir() if p.is_dir() and (p / 'metadata.json').exists()])\nprint(f'Total episodes found: {len(episodes)}')\nif episodes:\n    reader = EpisodeReader(str(episodes[0]))\n    print('Metadata:', json.dumps(reader.metadata, indent=2))"),
        ("code", "if episodes:\n    scorer = QualityScorer()\n    audit = scorer.audit_episode(str(episodes[0]))\n    print('Quality Audit:', json.dumps(audit, indent=2))")
    ]
)

# 2. trajectory_analysis.ipynb
create_nb(
    "trajectory_analysis.ipynb",
    "Robot Trajectory & Joint Kinematics Analysis",
    [
        ("markdown", "# JARVIS-PiPER :: Robot Trajectory & Kinematics Analysis\nAnalyzes joint position profiles, velocities, accelerations, and jerk across teleoperation demonstrations."),
        ("code", "import json\nimport numpy as np\nimport matplotlib.pyplot as plt\nfrom pathlib import Path\nimport sys\nsys.path.insert(0, str(Path.cwd().parent / 'python'))\nfrom evaluation.metrics import compute_trajectory_jerk\nprint('Imports successful!')"),
        ("code", "raw_dir = Path('../dataset/raw')\nepisodes = sorted([p for p in raw_dir.iterdir() if p.is_dir() and (p / 'trajectory.json').exists()])\nif episodes:\n    with open(episodes[0] / 'trajectory.json') as f:\n        data = json.load(f)\n    joints = np.array(data.get('joint_positions', []))\n    print(f'Joint trajectory shape: {joints.shape}')\n    if len(joints) > 5:\n        jerk = compute_trajectory_jerk(joints)\n        print(f'Trajectory RMS Jerk: {jerk:.4f}')"),
        ("code", "if 'joints' in locals() and len(joints) > 0:\n    plt.figure(figsize=(10, 4))\n    for j in range(min(6, joints.shape[1])):\n        plt.plot(joints[:, j], label=f'Joint {j+1}')\n    plt.title('PiPER 6-DOF Joint Positions over Time')\n    plt.xlabel('Timestep')\n    plt.ylabel('Angle (rad)')\n    plt.legend()\n    plt.grid(True)\n    plt.show()")
    ]
)

# 3. synchronization_analysis.ipynb
create_nb(
    "synchronization_analysis.ipynb",
    "Multimodal Synchronization & Jitter Analysis",
    [
        ("markdown", "# JARVIS-PiPER :: Multimodal Synchronization & Jitter Analysis\nQuantifies temporal alignment, frame delta distributions, and dropped packets."),
        ("code", "import json\nimport numpy as np\nimport matplotlib.pyplot as plt\nfrom pathlib import Path\nimport sys\nsys.path.insert(0, str(Path.cwd().parent / 'python'))\nfrom evaluation.metrics import compute_sync_jitter\nprint('Imports successful!')"),
        ("code", "raw_dir = Path('../dataset/raw')\nepisodes = sorted([p for p in raw_dir.iterdir() if p.is_dir() and (p / 'trajectory.json').exists()])\nif episodes:\n    with open(episodes[0] / 'trajectory.json') as f:\n        data = json.load(f)\n    ts = data.get('timestamps', [])\n    stats = compute_sync_jitter(ts, expected_hz=50.0)\n    print('Synchronization Jitter Stats:', json.dumps(stats, indent=2))"),
        ("code", "if 'ts' in locals() and len(ts) > 1:\n    diffs_ms = np.diff(ts) * 1000.0\n    plt.figure(figsize=(8, 4))\n    plt.hist(diffs_ms, bins=30, color='teal', edgecolor='black')\n    plt.title('Inter-Frame Time Delta Distribution (Expected: 20 ms)')\n    plt.xlabel('Delta t (ms)')\n    plt.ylabel('Frame Count')\n    plt.grid(True)\n    plt.show()")
    ]
)

# 4. world_state_analysis.ipynb
create_nb(
    "world_state_analysis.ipynb",
    "3D World State & Task Phase Segmentation",
    [
        ("markdown", "# JARVIS-PiPER :: 3D World State & Phase Segmentation\nSegments demonstrations into manipulation sub-tasks (Approach, Grasp, Transport, Release)."),
        ("code", "import json\nimport numpy as np\nfrom pathlib import Path\nimport sys\nsys.path.insert(0, str(Path.cwd().parent / 'python'))\nfrom world_model.segmenter import PhaseSegmenter\nfrom world_model.spatial import ForwardKinematics\nprint('Imports successful!')"),
        ("code", "fk = ForwardKinematics()\nq_sample = [0.0, 0.5, -0.5, 0.0, 0.2, 0.0]\ntcp_pose = fk.compute_tcp_pose(q_sample)\nprint('Forward Kinematics TCP Pose:', tcp_pose)"),
        ("code", "raw_dir = Path('../dataset/raw')\nepisodes = sorted([p for p in raw_dir.iterdir() if p.is_dir() and (p / 'trajectory.json').exists()])\nif episodes:\n    segmenter = PhaseSegmenter()\n    phases = segmenter.segment_episode(str(episodes[0]))\n    print('Detected Manipulation Phases:', phases)")
    ]
)

# 5. vjepa_visualization.ipynb
create_nb(
    "vjepa_visualization.ipynb",
    "V-JEPA Latent Representations & Trajectory Rollouts",
    [
        ("markdown", "# JARVIS-PiPER :: V-JEPA Latent Space Trajectories\nVisualizes high-dimensional video embeddings and predicted rollouts in 2D/3D latent projections."),
        ("code", "import numpy as np\nimport matplotlib.pyplot as plt\nfrom pathlib import Path\nimport sys\nsys.path.insert(0, str(Path.cwd().parent / 'python'))\nfrom world_model.vjepa import VJEPAConfig, VJEPAModel, visualize_latent_trajectory\nprint('Imports successful!')"),
        ("code", "cfg = VJEPAConfig()\nprint('V-JEPA Config:', cfg)\nt = np.linspace(0, 4*np.pi, 50)\nlatents = np.zeros((50, 128))\nlatents[:, 0] = np.sin(t)\nlatents[:, 1] = np.cos(t)\nlatents[:, 2] = t * 0.05\nprint('Synthesized Latent Trajectory shape:', latents.shape)"),
        ("code", "visualize_latent_trajectory(latents, output_png='../experiments/notebook_vjepa_trajectory.png')\nprint('Visualization generated in experiments/notebook_vjepa_trajectory.png')")
    ]
)
print("ALL 5 NOTEBOOKS GENERATED!")
