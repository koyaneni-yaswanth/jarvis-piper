import os
import sys

# Ensure root and python/ directories are always in sys.path during pytest execution
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
python_dir = os.path.join(root_dir, "python")

if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
if python_dir not in sys.path:
    sys.path.insert(0, python_dir)

# Pre-initialize Triton before any OpenGL/MuJoCo contexts are created.
# On Linux systems with Mesa EGL/LLVM, importing Triton after MuJoCo Renderer EGL has loaded
# causes a dynamic linker collision segfault. Pre-loading Triton guarantees safe co-existence.
try:
    import triton  # noqa: F401
except Exception:
    pass

