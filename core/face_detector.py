"""
人脸检测模块 —— MediaPipe Face Mesh (478 关键点)
"""
import cv2
import numpy as np
from typing import Tuple, Optional, List
from dataclasses import dataclass
from utils import logger, get_config

try:
    import mediapipe as mp
    HAS_MEDIAPIPE = True
except ImportError:
    HAS_MEDIAPIPE = False
    logger.warning("MediaPipe 未安装，人脸检测将不可用")


@dataclass
class FaceData:
    """单帧人脸数据"""
    landmarks_478: np.ndarray          # (478, 3) — x,y,z 归一化坐标
    bbox: Tuple[int, int, int, int]    # (x, y, w, h)
    confidence: float
    timestamp: float


class FaceDetector:
    """
    MediaPipe Face Mesh 封装
    — 实时检测 478 个人脸关键点
    — 输出归一化 landmark 及包围盒
    """

    def __init__(self):
        cfg = get_config()["face"]
        self.max_faces = cfg["max_faces"]
        self.detect_conf = cfg["detection_confidence"]
        self.track_conf = cfg["tracking_confidence"]
        self.refine = cfg["refine_landmarks"]

        if not HAS_MEDIAPIPE:
            self.mesh = None
            return

        self.mp_face_mesh = mp.solutions.face_mesh
        self.mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=self.max_faces,
            refine_landmarks=self.refine,
            min_detection_confidence=self.detect_conf,
            min_tracking_confidence=self.track_conf,
        )
        self.drawing = mp.solutions.drawing_utils
        # 兼容 MediaPipe 不同版本的 API 拼写
        try:
            self.draw_spec = mp.solutions.drawing_styles.get_default_face_mesh_tessellation_style()
        except AttributeError:
            self.draw_spec = mp.solutions.drawing_styles.get_default_face_mesh_tesselation_style()
        logger.info("FaceDetector 初始化完成 (MediaPipe Face Mesh)")

    def detect(self, frame_bgr: np.ndarray) -> Optional[FaceData]:
        """
        输入 BGR 帧 → 返回主要人脸数据 (或 None)
        """
        if self.mesh is None:
            return None

        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        results = self.mesh.process(rgb)
        rgb.flags.writeable = True

        if results.multi_face_landmarks is None:
            return None

        h, w = frame_bgr.shape[:2]
        # 取第一张脸
        lm_list = results.multi_face_landmarks[0]
        landmarks = np.array([
            [pt.x, pt.y, pt.z] for pt in lm_list.landmark
        ], dtype=np.float32)

        # 包围盒
        xs = landmarks[:, 0] * w
        ys = landmarks[:, 1] * h
        x_min, x_max = int(np.min(xs)), int(np.max(xs))
        y_min, y_max = int(np.min(ys)), int(np.max(ys))
        bbox = (x_min, y_min, x_max - x_min, y_max - y_min)

        return FaceData(
            landmarks_478=landmarks,
            bbox=bbox,
            confidence=1.0,
            timestamp=cv2.getTickCount() / cv2.getTickFrequency(),
        )

    def draw_landmarks(self, frame_bgr: np.ndarray,
                       landmarks: np.ndarray,
                       indices: List[int] = None) -> np.ndarray:
        """在帧上绘制关键点（调试用）"""
        h, w = frame_bgr.shape[:2]
        idxs = indices or range(478)
        for i in idxs:
            x = int(landmarks[i, 0] * w)
            y = int(landmarks[i, 1] * h)
            cv2.circle(frame_bgr, (x, y), 1, (0, 255, 0), -1)
        return frame_bgr

    def release(self):
        if self.mesh:
            self.mesh.close()
