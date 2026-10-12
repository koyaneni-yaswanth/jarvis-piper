#!/usr/bin/env python3
"""
Validates that all commands documented in README.md execute cleanly with expected return codes.
"""

import subprocess
import sys


import os

def run_cmd(cmd_list):
    print(f"\n--- Testing command: {' '.join(cmd_list)} ---")
    env = os.environ.copy()
    python_dir = os.path.abspath("python")
    cur_pypath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{python_dir}{os.pathsep}{cur_pypath}" if cur_pypath else python_dir
    res = subprocess.run(cmd_list, capture_output=True, text=True, env=env)
    if res.returncode != 0:
        print(f"[FAIL] Return code {res.returncode}")
        print("STDERR:\n", res.stderr)
        return False
    print("[PASS] Command succeeded.")
    return True


def main():
    print("=" * 80)
    print("        README.MD DOCUMENTED COMMAND SUITE VERIFICATION")
    print("=" * 80)

    commands = [
        [sys.executable, "python/jarvis_piper/cli/main.py", "version"],
        [sys.executable, "python/jarvis_piper/cli/main.py", "doctor"],
        [sys.executable, "python/jarvis_piper/cli/main.py", "demo", "--episodes", "2", "--steps", "30", "--output-dir", "dataset/test_demo"],
        [sys.executable, "python/jarvis_piper/cli/main.py", "validate", "--dataset", "dataset/test_demo"],
        [sys.executable, "python/jarvis_piper/cli/main.py", "export", "--format", "all", "--raw-dir", "dataset/test_demo", "--export-dir", "dataset/test_exported"],
        [sys.executable, "scripts/robot_model_audit.py"],
        [sys.executable, "scripts/isaac/isaac_doctor.py"],
        [sys.executable, "scripts/isaac/test_isaac_headless.py"],
        [sys.executable, "scripts/policy_dry_run.py"],
    ]

    all_ok = True
    for cmd in commands:
        if not run_cmd(cmd):
            all_ok = False
            break

    print("=" * 80)
    if all_ok:
        print(" [PASSED] ALL README.md COMMANDS VALIDATED SUCCESSFULLY!")
    else:
        print(" [FAILED] One or more commands failed.")
    print("=" * 80)
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
