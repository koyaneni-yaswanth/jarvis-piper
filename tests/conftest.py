import os
import sys

# Ensure root and python/ directories are always in sys.path during pytest execution
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
python_dir = os.path.join(root_dir, "python")

if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
if python_dir not in sys.path:
    sys.path.insert(0, python_dir)

