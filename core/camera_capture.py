"""
摄像头采集模块 — OpenCV 实时摄像头
支持: PC Webcam / Android Camera2 (via python-for-android)
"""
import threading
import time
from typing import Optional, Tuple, Callable
import numpy as np
from utils import logger, get_config
from utils.platform_utils import is_android, get_camera_id

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False
    logger.warning("OpenCV 未安装，摄像头不可用")


class CameraCapture:
    """
    实时摄像头采集
    - 后台线程连续读取帧
    - 自动处理横竖屏旋转
    - 支持帧回调
    """

    def __init__(self):
        self.cfg = get_config()
        self.camera_id: int = get_camera_id()  # 平台自适应
        self.width: int = 640
        self.height: int = 480
        self.fps: int = 30
        self.rotate_deg: int = 90 if is_android() else 0  # 前置摄像头旋转

        self._cap: Optional[cv2.VideoCapture] = None
        self._running: bool = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._latest_frame: Optional[np.ndarray] = None
        self._frame_callback: Optional[Callable[[np.ndarray], None]] = None

        # 平台检测
        self._is_android: bool = False
        try:
            from android.permissions import request_permissions, Permission
            self._is_android = True
        except ImportError:
            pass

    # ------------------------------------------------------------
    # 生命周期
    # ------------------------------------------------------------
    def open(self, camera_id: int = 0) -> bool:
        """打开摄像头"""
        self.camera_id = camera_id

        if self._is_android:
            return self._open_android()

        if not HAS_CV2:
            logger.error("OpenCV 不可用")
            return False

        self._cap = cv2.VideoCapture(camera_id)
        # 移动端前置摄像头
        if camera_id == 1 or camera_id == -1:
            self._cap = cv2.VideoCapture(camera_id)
        if not self._cap.isOpened():
            logger.error(f"无法打开摄像头 #{camera_id}")
            return False

        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self._cap.set(cv2.CAP_PROP_FPS, self.fps)
        self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        logger.info(f"摄像头 #{camera_id} 已打开 ({self.width}x{self.height})")
        return True

    def _open_android(self) -> bool:
        """Android 平台打开摄像头"""
        try:
            from android.permissions import request_permissions, Permission
            request_permissions([
                Permission.CAMERA,
                Permission.RECORD_AUDIO,
            ])

            # 使用 python-for-android 的 camera 模块
            # 或者通过 android.hardware 的 Camera2 API
            import android
            from android.hardware import Camera
            self._android_camera = Camera.open(self.camera_id)
            self._android_camera.setPreviewSize(self.width, self.height)
            logger.info(f"Android 摄像头 #{self.camera_id} 已打开")
            return True
        except Exception as e:
            logger.error(f"Android 摄像头打开失败: {e}")
            return False

    def start(self, callback: Optional[Callable[[np.ndarray], None]] = None):
        """启动后台采集线程"""
        if self._running:
            return
        self._running = True
        self._frame_callback = callback
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        logger.info("摄像头采集线程已启动")

    def stop(self):
        """停止采集"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        logger.info("摄像头采集已停止")

    def close(self):
        """释放摄像头"""
        self.stop()
        if self._cap:
            self._cap.release()
            self._cap = None
        logger.info("摄像头已释放")

    # ------------------------------------------------------------
    # 采集循环
    # ------------------------------------------------------------
    def _capture_loop(self):
        """后台帧采集"""
        frame_time = 1.0 / max(self.fps, 1)
        last_time = time.time()

        while self._running:
            ret, frame = False, None

            if self._is_android:
                ret, frame = self._capture_android()
            elif self._cap:
                ret, frame = self._cap.read()
                if ret and self.rotate_deg:
                    frame = self._rotate_frame(frame)

            if ret and frame is not None:
                with self._lock:
                    self._latest_frame = frame.copy()

                if self._frame_callback:
                    try:
                        self._frame_callback(frame)
                    except Exception as e:
                        logger.error(f"帧回调异常: {e}")

            # 帧率控制
            elapsed = time.time() - last_time
            sleep_time = max(0, frame_time - elapsed)
            if sleep_time > 0.001:
                time.sleep(sleep_time)
            last_time = time.time()

    def _capture_android(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Android 平台帧捕获"""
        try:
            # 通过 android.hardware 或 surface 获取预览帧
            # 此处为占位，实际需根据 python-for-android 的 camera recipe 调整
            return False, None
        except Exception:
            return False, None

    def _rotate_frame(self, frame: np.ndarray) -> np.ndarray:
        """旋转/镜像帧"""
        if self.rotate_deg == 90:
            frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
        elif self.rotate_deg == 270:
            frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
        elif self.rotate_deg == 180:
            frame = cv2.rotate(frame, cv2.ROTATE_180)
        return frame

    # ------------------------------------------------------------
    # 帧获取
    # ------------------------------------------------------------
    def get_frame(self) -> Optional[np.ndarray]:
        """获取最新帧（非阻塞）"""
        with self._lock:
            return self._latest_frame.copy() if self._latest_frame is not None else None

    def read_frame_blocking(self, timeout: float = 2.0) -> Optional[np.ndarray]:
        """阻塞等待一帧"""
        start = time.time()
        while time.time() - start < timeout:
            frame = self.get_frame()
            if frame is not None:
                return frame
            time.sleep(0.01)
        return None

    @property
    def is_opened(self) -> bool:
        return self._cap is not None and self._cap.isOpened()

    @property
    def is_running(self) -> bool:
        return self._running