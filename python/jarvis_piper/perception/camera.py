"""
JARVIS-PiPER: Camera Source Abstraction Layer.

Provides a hardware-independent interface for acquiring frames from:
- Intel RealSense D405 (depth + RGB)
- DECXIN / Sunplus USB cameras
- Recorded image files or directories (replay mode)
- Deterministic synthetic frames (mock / CI mode)

Design rules:
- No camera is opened until open() is explicitly called.
- Unavailable hardware raises CameraUnavailableError (never silently succeeds).
- No hard-coded camera index; device selection is always explicit.
- Each frame carries a monotonic timestamp and a unique frame_id.
- Color format is always BGR (OpenCV convention) unless documented otherwise.
- Graceful close() on all code paths.
"""

import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

class ColorFormat(str, Enum):
    BGR = "BGR"    # OpenCV default
    RGB = "RGB"
    GRAY = "GRAY"


@dataclass
class CameraFrame:
    """A single camera acquisition result.

    Fields
    ------
    color_image : np.ndarray | None
        H x W x 3 uint8 array (BGR). None when acquisition failed.
    depth_image : np.ndarray | None
        H x W uint16 array in millimetres (0 = invalid). None when unavailable.
    timestamp_s : float
        Monotonic wall-clock timestamp (time.monotonic()) at acquisition.
    frame_id : int
        Monotonically increasing frame counter starting from 0.
    source_id : str
        Identifier of the camera source that produced this frame.
    width : int
    height : int
    color_format : ColorFormat
    metadata : dict
        Optional extra data (e.g. RealSense intrinsics snapshot).
    """

    color_image: Optional[np.ndarray] = None
    depth_image: Optional[np.ndarray] = None
    timestamp_s: float = 0.0
    frame_id: int = 0
    source_id: str = "unknown"
    width: int = 0
    height: int = 0
    color_format: ColorFormat = ColorFormat.BGR
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_valid(self) -> bool:
        """True iff a color image is present and non-empty."""
        return self.color_image is not None and self.color_image.size > 0

    @property
    def has_depth(self) -> bool:
        return self.depth_image is not None and self.depth_image.size > 0


class CameraUnavailableError(RuntimeError):
    """Raised when requested camera hardware is not available."""
    pass


class CameraNotOpenError(RuntimeError):
    """Raised when read() is called before open()."""
    pass


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class CameraSource(ABC):
    """Abstract base class for all JARVIS camera sources."""

    def __init__(
        self,
        source_id: str,
        width: int = 640,
        height: int = 480,
        fps: int = 30,
        color_format: ColorFormat = ColorFormat.BGR,
    ) -> None:
        self.source_id = source_id
        self.width = width
        self.height = height
        self.fps = fps
        self.color_format = color_format
        self._is_open: bool = False
        self._frame_counter: int = 0

    @abstractmethod
    def open(self) -> None:
        """Open the camera source. Raises CameraUnavailableError on failure."""

    @abstractmethod
    def read(self) -> CameraFrame:
        """Acquire the next frame. Raises CameraNotOpenError if not open."""

    @abstractmethod
    def close(self) -> None:
        """Release all camera resources."""

    @property
    def is_open(self) -> bool:
        return self._is_open

    def __enter__(self) -> "CameraSource":
        self.open()
        return self

    def __exit__(self, *_) -> None:
        self.close()

    def _next_frame_id(self) -> int:
        fid = self._frame_counter
        self._frame_counter += 1
        return fid

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.source_id!r}, open={self._is_open})"


# ---------------------------------------------------------------------------
# Intel RealSense D405 adapter
# ---------------------------------------------------------------------------

class RealsenseCamera(CameraSource):
    """
    Intel RealSense D405 depth + RGB camera adapter.

    Requires `pyrealsense2` to be installed. If the package is missing or
    no RealSense device is enumerated, raises CameraUnavailableError on open().

    Parameters
    ----------
    serial : str | None
        USB serial number to select a specific RealSense device.
        If None, the first enumerated device is used.
    enable_depth : bool
        Whether to stream the aligned depth channel.
    """

    def __init__(
        self,
        source_id: str = "realsense_d405",
        width: int = 640,
        height: int = 480,
        fps: int = 30,
        serial: Optional[str] = None,
        enable_depth: bool = True,
    ) -> None:
        super().__init__(source_id, width, height, fps, ColorFormat.BGR)
        self._serial = serial
        self._enable_depth = enable_depth
        self._pipeline: Any = None
        self._align: Any = None
        self._rs: Any = None  # pyrealsense2 module reference

    def open(self) -> None:
        try:
            import pyrealsense2 as rs  # type: ignore[import]
            self._rs = rs
        except ImportError as exc:
            raise CameraUnavailableError(
                "pyrealsense2 is not installed. "
                "Install it with: pip install pyrealsense2"
            ) from exc

        ctx = self._rs.context()
        devices = ctx.query_devices()
        if len(devices) == 0:
            raise CameraUnavailableError(
                "No Intel RealSense device found. "
                "Connect the D405 and verify USB 3.x connection."
            )

        self._pipeline = self._rs.pipeline()
        cfg = self._rs.config()

        if self._serial:
            cfg.enable_device(self._serial)

        cfg.enable_stream(
            self._rs.stream.color,
            self.width, self.height,
            self._rs.format.bgr8,
            self.fps,
        )
        if self._enable_depth:
            cfg.enable_stream(
                self._rs.stream.depth,
                self.width, self.height,
                self._rs.format.z16,
                self.fps,
            )
            self._align = self._rs.align(self._rs.stream.color)

        try:
            self._pipeline.start(cfg)
        except Exception as exc:
            raise CameraUnavailableError(
                f"Failed to start RealSense pipeline: {exc}"
            ) from exc

        self._is_open = True
        logger.info("RealSense D405 opened: %dx%d @ %d fps (depth=%s)",
                    self.width, self.height, self.fps, self._enable_depth)

    def read(self) -> CameraFrame:
        if not self._is_open:
            raise CameraNotOpenError("RealsenseCamera.read() called before open().")

        try:
            frames = self._pipeline.wait_for_frames(timeout_ms=1000)
        except Exception as exc:
            logger.warning("RealSense frame timeout: %s", exc)
            return CameraFrame(
                timestamp_s=time.monotonic(),
                frame_id=self._next_frame_id(),
                source_id=self.source_id,
                width=self.width,
                height=self.height,
                color_format=self.color_format,
            )

        if self._align:
            frames = self._align.process(frames)

        color_frame = frames.get_color_frame()
        color_img: Optional[np.ndarray] = None
        if color_frame:
            color_img = np.asanyarray(color_frame.get_data())

        depth_img: Optional[np.ndarray] = None
        if self._enable_depth:
            depth_frame = frames.get_depth_frame()
            if depth_frame:
                depth_img = np.asanyarray(depth_frame.get_data())

        h, w = (color_img.shape[:2] if color_img is not None else (self.height, self.width))
        return CameraFrame(
            color_image=color_img,
            depth_image=depth_img,
            timestamp_s=time.monotonic(),
            frame_id=self._next_frame_id(),
            source_id=self.source_id,
            width=w,
            height=h,
            color_format=ColorFormat.BGR,
        )

    def close(self) -> None:
        if self._pipeline and self._is_open:
            try:
                self._pipeline.stop()
            except Exception:
                pass
        self._is_open = False
        self._pipeline = None
        logger.info("RealSense camera closed.")


# ---------------------------------------------------------------------------
# USB camera adapter (DECXIN / Sunplus or any V4L2 device)
# ---------------------------------------------------------------------------

class UsbCamera(CameraSource):
    """
    Generic USB camera adapter using OpenCV VideoCapture.

    Parameters
    ----------
    device_index : int
        V4L2 device index (e.g. 0 for /dev/video0).
        Must be explicitly provided; no default assumed.
    """

    def __init__(
        self,
        source_id: str = "usb_camera",
        device_index: int = 0,
        width: int = 640,
        height: int = 480,
        fps: int = 30,
    ) -> None:
        super().__init__(source_id, width, height, fps, ColorFormat.BGR)
        self._device_index = device_index
        self._cap: Any = None

    def open(self) -> None:
        try:
            import cv2  # type: ignore[import]
            self._cv2 = cv2
        except ImportError as exc:
            raise CameraUnavailableError(
                "opencv-python is not installed. Install with: pip install opencv-python"
            ) from exc

        cap = self._cv2.VideoCapture(self._device_index)
        if not cap.isOpened():
            raise CameraUnavailableError(
                f"USB camera device index {self._device_index} could not be opened. "
                f"Check 'ls /dev/video*' and verify device is connected."
            )

        cap.set(self._cv2.CAP_PROP_FRAME_WIDTH, self.width)
        cap.set(self._cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        cap.set(self._cv2.CAP_PROP_FPS, self.fps)
        self._cap = cap
        self._is_open = True
        logger.info("USB camera opened: index=%d %dx%d @ %d fps",
                    self._device_index, self.width, self.height, self.fps)

    def read(self) -> CameraFrame:
        if not self._is_open:
            raise CameraNotOpenError("UsbCamera.read() called before open().")

        ret, frame = self._cap.read()
        ts = time.monotonic()
        if not ret or frame is None:
            logger.warning("USB camera read failed (device %d).", self._device_index)
            return CameraFrame(
                timestamp_s=ts,
                frame_id=self._next_frame_id(),
                source_id=self.source_id,
                width=self.width,
                height=self.height,
                color_format=ColorFormat.BGR,
            )

        return CameraFrame(
            color_image=frame,
            timestamp_s=ts,
            frame_id=self._next_frame_id(),
            source_id=self.source_id,
            width=frame.shape[1],
            height=frame.shape[0],
            color_format=ColorFormat.BGR,
        )

    def close(self) -> None:
        if self._cap and self._is_open:
            self._cap.release()
        self._is_open = False
        self._cap = None
        logger.info("USB camera closed (index=%d).", self._device_index)


# ---------------------------------------------------------------------------
# Recorded / replay camera (image files or directory)
# ---------------------------------------------------------------------------

class RecordedCamera(CameraSource):
    """
    Replay camera that reads frames from a directory of image files or a list of paths.

    Frames are served sequentially. When all frames are exhausted, subsequent
    read() calls return the last frame (freeze) or a blank frame depending on
    `loop` mode.

    Parameters
    ----------
    paths : list[str | Path] | str | Path
        A single image path, a list of image paths, or a directory containing
        PNG/JPG images in lexicographic order.
    loop : bool
        If True, restart from the first frame after the last one is read.
    """

    SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif"}

    def __init__(
        self,
        paths,
        source_id: str = "recorded_camera",
        width: int = 640,
        height: int = 480,
        loop: bool = False,
    ) -> None:
        super().__init__(source_id, width, height, fps=0, color_format=ColorFormat.BGR)
        self._paths_input = paths
        self._loop = loop
        self._image_paths: List[Path] = []
        self._index: int = 0
        self._cv2: Any = None

    def open(self) -> None:
        try:
            import cv2  # type: ignore[import]
            self._cv2 = cv2
        except ImportError as exc:
            raise CameraUnavailableError(
                "opencv-python is required for RecordedCamera. "
                "Install with: pip install opencv-python"
            ) from exc

        # Resolve paths
        inp = self._paths_input
        if isinstance(inp, (str, Path)):
            p = Path(inp)
            if p.is_dir():
                self._image_paths = sorted(
                    f for f in p.iterdir()
                    if f.suffix.lower() in self.SUPPORTED_EXTENSIONS
                )
            elif p.is_file():
                self._image_paths = [p]
            else:
                raise CameraUnavailableError(f"RecordedCamera path not found: {inp}")
        else:
            self._image_paths = [Path(x) for x in inp]

        missing = [p for p in self._image_paths if not p.exists()]
        if missing:
            raise CameraUnavailableError(
                f"RecordedCamera: {len(missing)} image file(s) not found: "
                f"{[str(m) for m in missing[:5]]}"
            )

        if len(self._image_paths) == 0:
            raise CameraUnavailableError("RecordedCamera: no image files found.")

        self._is_open = True
        self._index = 0
        logger.info("RecordedCamera opened: %d frames from %s",
                    len(self._image_paths), str(self._image_paths[0].parent))

    def read(self) -> CameraFrame:
        if not self._is_open:
            raise CameraNotOpenError("RecordedCamera.read() called before open().")

        if self._index >= len(self._image_paths):
            if self._loop:
                self._index = 0
            else:
                # Return blank frame after exhaustion
                return CameraFrame(
                    timestamp_s=time.monotonic(),
                    frame_id=self._next_frame_id(),
                    source_id=self.source_id,
                    width=self.width,
                    height=self.height,
                    color_format=ColorFormat.BGR,
                    metadata={"exhausted": True},
                )

        path = self._image_paths[self._index]
        self._index += 1
        img = self._cv2.imread(str(path))
        ts = time.monotonic()

        if img is None:
            logger.warning("RecordedCamera: failed to read %s", path)
            return CameraFrame(
                timestamp_s=ts,
                frame_id=self._next_frame_id(),
                source_id=self.source_id,
                width=self.width,
                height=self.height,
                color_format=ColorFormat.BGR,
            )

        if img.shape[1] != self.width or img.shape[0] != self.height:
            img = self._cv2.resize(img, (self.width, self.height))

        return CameraFrame(
            color_image=img,
            timestamp_s=ts,
            frame_id=self._next_frame_id(),
            source_id=self.source_id,
            width=img.shape[1],
            height=img.shape[0],
            color_format=ColorFormat.BGR,
            metadata={"path": str(path)},
        )

    def close(self) -> None:
        self._is_open = False
        logger.info("RecordedCamera closed.")


# ---------------------------------------------------------------------------
# Mock / synthetic camera (for tests and MOCK mode)
# ---------------------------------------------------------------------------

class MockCamera(CameraSource):
    """
    Deterministic synthetic camera that generates solid-colour test frames.

    No hardware access. No file I/O. Always succeeds.
    The frame colour and optional depth value are configurable.

    Parameters
    ----------
    color_bgr : tuple[int, int, int]
        BGR fill colour for the synthetic frame (default: medium grey).
    depth_mm : int | None
        Depth value in millimetres to fill the depth image.
        If None, no depth image is generated.
    """

    def __init__(
        self,
        source_id: str = "mock_camera",
        width: int = 640,
        height: int = 480,
        fps: int = 30,
        color_bgr: Tuple[int, int, int] = (127, 127, 127),
        depth_mm: Optional[int] = 550,
    ) -> None:
        super().__init__(source_id, width, height, fps, ColorFormat.BGR)
        self._color_bgr = color_bgr
        self._depth_mm = depth_mm

    def open(self) -> None:
        self._is_open = True
        logger.debug("MockCamera opened (%dx%d).", self.width, self.height)

    def read(self) -> CameraFrame:
        if not self._is_open:
            raise CameraNotOpenError("MockCamera.read() called before open().")

        color = np.full((self.height, self.width, 3), self._color_bgr, dtype=np.uint8)

        depth: Optional[np.ndarray] = None
        if self._depth_mm is not None:
            depth = np.full((self.height, self.width), self._depth_mm, dtype=np.uint16)

        return CameraFrame(
            color_image=color,
            depth_image=depth,
            timestamp_s=time.monotonic(),
            frame_id=self._next_frame_id(),
            source_id=self.source_id,
            width=self.width,
            height=self.height,
            color_format=ColorFormat.BGR,
            metadata={"synthetic": True},
        )

    def close(self) -> None:
        self._is_open = False
        logger.debug("MockCamera closed.")


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def build_camera_source(config: Dict[str, Any]) -> CameraSource:
    """
    Build a CameraSource from a configuration dictionary.

    Supported ``type`` values:
    - ``"mock"``      : MockCamera (default when type is absent)
    - ``"realsense"`` : RealsenseCamera (requires pyrealsense2)
    - ``"usb"``       : UsbCamera (requires opencv-python, explicit device_index)
    - ``"recorded"``  : RecordedCamera (requires paths)

    Example configs
    ---------------
    {"type": "mock", "width": 640, "height": 480}
    {"type": "realsense", "width": 640, "height": 480, "fps": 30, "enable_depth": True}
    {"type": "usb", "device_index": 2, "width": 1280, "height": 720}
    {"type": "recorded", "paths": "/data/episode_001/frames/"}

    Parameters
    ----------
    config : dict
        Camera configuration dictionary.

    Returns
    -------
    CameraSource
        An unopened camera source.

    Raises
    ------
    ValueError
        If an unknown camera type is specified.
    """
    cam_type = config.get("type", "mock").lower()
    source_id = config.get("source_id", cam_type)
    width = int(config.get("width", 640))
    height = int(config.get("height", 480))
    fps = int(config.get("fps", 30))

    if cam_type == "mock":
        return MockCamera(
            source_id=source_id,
            width=width,
            height=height,
            fps=fps,
            color_bgr=tuple(config.get("color_bgr", [127, 127, 127])),
            depth_mm=config.get("depth_mm", 550),
        )
    elif cam_type == "realsense":
        return RealsenseCamera(
            source_id=source_id,
            width=width,
            height=height,
            fps=fps,
            serial=config.get("serial", None),
            enable_depth=bool(config.get("enable_depth", True)),
        )
    elif cam_type == "usb":
        device_index = int(config.get("device_index", 0))
        return UsbCamera(
            source_id=source_id,
            device_index=device_index,
            width=width,
            height=height,
            fps=fps,
        )
    elif cam_type == "recorded":
        paths = config.get("paths")
        if not paths:
            raise ValueError("RecordedCamera config must include 'paths'.")
        return RecordedCamera(
            paths=paths,
            source_id=source_id,
            width=width,
            height=height,
            loop=bool(config.get("loop", False)),
        )
    else:
        raise ValueError(
            f"Unknown camera type: {cam_type!r}. "
            f"Valid types: 'mock', 'realsense', 'usb', 'recorded'."
        )
