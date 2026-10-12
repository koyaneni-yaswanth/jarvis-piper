import os
import sys

# Ensure python/ directory is always in sys.path during pytest execution
python_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "python"))
if python_dir not in sys.path:
    sys.path.insert(0, python_dir)
