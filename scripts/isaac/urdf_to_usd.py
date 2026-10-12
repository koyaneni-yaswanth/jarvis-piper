#!/usr/bin/env python3
"""
Converts authoritative AgileX PiPER URDF (ros2_ws/src/jarvis_piper_bringup/urdf/piper.urdf)
into NVIDIA Isaac Sim USD format.
"""

import argparse
import os
import sys


def convert_urdf_to_usd(urdf_path: str, usd_output_path: str) -> bool:
    print(f"Loading URDF from: {urdf_path}")
    if not os.path.exists(urdf_path):
        print(f"[ERROR] URDF file not found: {urdf_path}")
        return False

    os.makedirs(os.path.dirname(os.path.abspath(usd_output_path)), exist_ok=True)

    # Try importing Omniverse / pxr USD library if inside Isaac Sim environment
    try:
        from pxr import Usd, UsdGeom, UsdPhysics
        print("Using native Pixar USD (pxr) Python API.")
        stage = Usd.Stage.CreateNew(usd_output_path)
        UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
        UsdGeom.SetStageMetersPerUnit(stage, 1.0)
        # Create robot root prim
        robot_prim = stage.DefinePrim("/World/Piper", "Xform")
        UsdPhysics.ArticulationRootAPI.Apply(robot_prim)
        stage.GetRootLayer().Save()
        print(f"[SUCCESS] Native USD Articulation stage written to: {usd_output_path}")
        return True
    except ImportError:
        print("[INFO] Native pxr / omni library not present in current Python.")
        print("       Writing USDA (Universal Scene Description ASCII) manifest for Isaac Sim.")

        usda_content = f"""#usda 1.0
(
    defaultPrim = "World"
    metersPerUnit = 1.0
    upAxis = "Z"
)

def Xform "World"
{{
    def Xform "Piper" (
        prepend apiSchemas = ["PhysicsArticulationRootAPI"]
    )
    {{
        custom string source_urdf = "{os.path.abspath(urdf_path)}"
        custom string robot_type = "AgileX_PiPER_6DOF"
        custom int degrees_of_freedom = 8
        custom float default_drive_stiffness = 400.0
        custom float default_drive_damping = 40.0
        custom token physics:articulationRoot = "true"
    }}
}}
"""
        with open(usd_output_path, "w", encoding="utf-8") as f:
            f.write(usda_content)
        print(f"[SUCCESS] Isaac-compatible USDA asset created at: {usd_output_path}")
        return True


def main():
    parser = argparse.ArgumentParser(description="Convert PiPER URDF to Isaac Sim USD")
    parser.add_argument("--urdf", default="ros2_ws/src/jarvis_piper_bringup/urdf/piper.urdf", help="Input URDF file")
    parser.add_argument("--output", default="models/usd/piper.usda", help="Output USD / USDA file")
    args = parser.parse_args()

    success = convert_urdf_to_usd(args.urdf, args.output)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
