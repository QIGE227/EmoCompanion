"""
情绪识别模块 —— 基于 MediaPipe 关键点 → 8 种基本情绪
策略：轻量 ONNX 分类器 / 或基于 FACS 动作单元的启发式规则
"""
import numpy as np
from typing import Tuple
from enum import IntEnum
from utils import logger, get_config

try:
    import onnxruntime as ort
    HAS_ONNX = True
except ImportError:
    HAS_ONNX = False
    logger.warning("onnxruntime 未安装，情绪识别将使用启发式规则")


class Emotion(IntEnum):
    HAPPY = 0
    ANGRY = 1
    SAD = 2
    SURPRISED = 3
    FEARFUL = 4
    DISGUSTED = 5
    NEUTRAL = 6
    CONFUSED = 7

    @property
    def cn_name(self) -> str:
        return {
            0: "开心", 1: "生气", 2: "难过", 3: "惊讶",
            4: "害怕", 5: "厌恶", 6: "中性", 7: "疑惑",
        }[self.value]

    @property
    def emoji(self) -> str:
        return {
            0: "😊", 1: "😠", 2: "😢", 3: "😲",
            4: "😨", 5: "🤢", 6: "😐", 7: "🤔",
        }[self.value]


class EmotionRecognizer:
    """
    情绪识别器：
    - 优先使用 ONNX 轻量模型
    - 回退到基于关键点几何特征的启发式规则
    """

    # ------------------------------------------------------------
    # 面部关键点索引 (MediaPipe 478点体系)
    # ------------------------------------------------------------
    # 眼睛区域 (左/右)
    EYE_LEFT_OUTER = 33;   EYE_LEFT_INNER = 133
    EYE_RIGHT_INNER = 362; EYE_RIGHT_OUTER = 263
    # 嘴角
    MOUTH_LEFT = 61;  MOUTH_RIGHT = 291
    MOUTH_TOP = 13;   MOUTH_BOTTOM = 14
    # 眉毛
    BROW_LEFT_INNER = 105;  BROW_LEFT_OUTER = 70
    BROW_RIGHT_INNER = 334; BROW_RIGHT_OUTER = 300
    # 鼻子
    NOSE_TIP = 1

    def __init__(self):
        cfg = get_config()["emotion"]
        self.num_classes = cfg["num_classes"]
        self.model_path = cfg["classifier_model"]

        self.onnx_session = None
        if HAS_ONNX and self.model_path:
            try:
                self.onnx_session = ort.InferenceSession(self.model_path)
                logger.info(f"情绪 ONNX 模型已加载: {self.model_path}")
            except Exception as e:
                logger.warning(f"ONNX 模型加载失败: {e}，回退启发式")

    def predict(self, landmarks: np.ndarray) -> Tuple[Emotion, float]:
        """
        landmarks: (478, 3) ndarray
        返回: (情绪枚举, 置信度)
        """
        if self.onnx_session is not None:
            return self._predict_onnx(landmarks)
        return self._predict_heuristic(landmarks)

    def _predict_onnx(self, lm: np.ndarray) -> Tuple[Emotion, float]:
        """ONNX 模型推理"""
        inp = lm.reshape(1, -1).astype(np.float32)
        out = self.onnx_session.run(None, {"input": inp})[0]
        idx = int(np.argmax(out))
        conf = float(np.max(out))
        return Emotion(idx), conf

    def _predict_heuristic(self, lm: np.ndarray) -> Tuple[Emotion, float]:
        """
        基于关键点几何特征的启发式情绪识别
        本实现提供基础规则，可替换为更精细的模型
        """
        # --- 计算几何特征 ---
        def dist(i, j):
            return np.linalg.norm(lm[i, :2] - lm[j, :2])

        eye_open = (dist(self.EYE_LEFT_OUTER, self.EYE_LEFT_INNER) +
                    dist(self.EYE_RIGHT_OUTER, self.EYE_RIGHT_INNER)) / 2
        mouth_open = dist(self.MOUTH_TOP, self.MOUTH_BOTTOM)
        mouth_width = dist(self.MOUTH_LEFT, self.MOUTH_RIGHT)
        # 眉毛高度（相对眼睛）
        brow_height = (
            (lm[self.BROW_LEFT_INNER, 1] + lm[self.BROW_RIGHT_INNER, 1]) / 2
            - (lm[self.EYE_LEFT_INNER, 1] + lm[self.EYE_RIGHT_INNER, 1]) / 2
        )

        # --- 规则判定 ---
        mouth_ratio = mouth_open / max(mouth_width, 1e-5)

        if mouth_ratio > 0.5 and eye_open > 0.12:
            return Emotion.SURPRISED, 0.75
        if mouth_ratio > 0.35:
            return Emotion.HAPPY, 0.7
        if brow_height < -0.02 and mouth_ratio < 0.05:
            return Emotion.ANGRY, 0.65
        if brow_height > 0.02 and mouth_ratio < 0.03:
            return Emotion.SAD, 0.6
        if eye_open > 0.14 and mouth_ratio < 0.02:
            return Emotion.FEARFUL, 0.55
        if mouth_ratio < 0.02 and abs(brow_height) < 0.015:
            return Emotion.NEUTRAL, 0.8

        return Emotion.NEUTRAL, 0.5
