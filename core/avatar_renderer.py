"""
数字人渲染模块 —— 2D/OpenGL 数字人渲染
支持: OpenGL 简单角色 | Live2D Cubism SDK
"""
import math
import numpy as np
from typing import Tuple, Optional, Dict
from dataclasses import dataclass
from utils import logger, get_config

try:
    from OpenGL.GL import *
    from OpenGL.GLU import *
    HAS_OPENGL = True
except ImportError:
    HAS_OPENGL = False
    logger.warning("PyOpenGL 未安装，数字人渲染仅支持 Pixmap 回退")

from core.emotion_recognizer import Emotion


@dataclass
class AvatarState:
    """数字人当前状态"""
    emotion: Emotion = Emotion.NEUTRAL
    emotion_intensity: float = 0.5          # 0.0 ~ 1.0
    mouth_openness: float = 0.0             # 唇形张开程度
    head_tilt_x: float = 0.0                # 头部俯仰
    head_tilt_y: float = 0.0                # 头部偏转
    blink: float = 0.0                      # 眨眼 (0=睁眼, 1=闭眼)
    gaze_x: float = 0.5                     # 视线 X (跟随用户)
    gaze_y: float = 0.5                     # 视线 Y


class AvatarRenderer:
    """
    数字人渲染器
    - backend=opengl: 简单程序化角色（可配置表情）
    - backend=live2d: Live2D Cubism SDK 驱动
    """

    # 表情参数映射 (情绪 → Live2D 参数 ID)
    EMOTION_TO_LIVE2D = {
        Emotion.HAPPY:     {"ParamMouth": 0.6, "ParamEye": 0.5, "ParamBrow": 0.3},
        Emotion.ANGRY:     {"ParamMouth": 0.2, "ParamEye": 0.4, "ParamBrow": -0.6},
        Emotion.SAD:       {"ParamMouth": 0.1, "ParamEye": 0.3, "ParamBrow": -0.4},
        Emotion.SURPRISED: {"ParamMouth": 0.9, "ParamEye": 0.9, "ParamBrow": 0.8},
        Emotion.FEARFUL:   {"ParamMouth": 0.7, "ParamEye": 0.8, "ParamBrow": 0.5},
        Emotion.DISGUSTED: {"ParamMouth": 0.3, "ParamEye": 0.3, "ParamBrow": -0.5},
        Emotion.NEUTRAL:   {"ParamMouth": 0.3, "ParamEye": 0.4, "ParamBrow": 0.0},
        Emotion.CONFUSED:  {"ParamMouth": 0.4, "ParamEye": 0.5, "ParamBrow": 0.5},
    }

    def __init__(self):
        cfg = get_config()["avatar"]
        self.backend = cfg["backend"]
        self.canvas_w = cfg["canvas_width"]
        self.canvas_h = cfg["canvas_height"]
        self.fps = cfg["fps"]
        self.live2d_path = cfg.get("live2d_model_path", "")
        self.avatar_image = cfg.get("avatar_image", "")

        self.state = AvatarState()
        self._blink_timer: float = 0.0
        self._next_blink: float = 3.0        # 随机眨眼间隔

        if self.backend == "live2d":
            self._init_live2d()
        else:
            self._init_opengl()

        logger.info(f"AvatarRenderer 初始化完成 (backend={self.backend})")

    def _init_opengl(self):
        """初始化 OpenGL 简单角色"""
        if not HAS_OPENGL:
            logger.warning("OpenGL 不可用，使用纯色回退")
            return

    def _init_live2d(self):
        """初始化 Live2D Cubism SDK"""
        try:
            # Live2D Cubism SDK for Native Python 绑定
            # 实际集成需参考官方 SDK 文档
            logger.info(f"Live2D 模型路径: {self.live2d_path}")
            # TODO: 正式集成 Cubism SDK
            # import live2d  # 需要自行编译 Python 绑定
        except Exception as e:
            logger.warning(f"Live2D 初始化受限: {e}")

    # ------------------------------------------------------------
    # 更新接口（每帧调用）
    # ------------------------------------------------------------
    def update_emotion(self, emotion: Emotion, intensity: float = 0.5):
        """更新当前情绪"""
        self.state.emotion = emotion
        self.state.emotion_intensity = intensity

    def update_mouth(self, openness: float):
        """更新唇形张开度 (0.0~1.0)"""
        self.state.mouth_openness = np.clip(openness, 0.0, 1.0)

    def update_head_pose(self, tilt_x: float, tilt_y: float):
        """更新头部姿态（基于关键点估算）"""
        self.state.head_tilt_x = tilt_x
        self.state.head_tilt_y = tilt_y

    def update_gaze(self, x: float, y: float):
        """更新视线方向"""
        self.state.gaze_x = x
        self.state.gaze_y = y

    def tick(self, dt: float):
        """每帧 tick：眨眼、随机微动等"""
        self._blink_timer += dt
        if self._blink_timer >= self._next_blink:
            self._blink_timer = 0.0
            self._next_blink = 2.0 + np.random.random() * 4.0
            self.state.blink = 1.0  # 触发眨眼
        else:
            # 眨眼衰减
            self.state.blink = max(0.0, self.state.blink - dt * 5.0)

    # ------------------------------------------------------------
    # 渲染 (OpenGL)
    # ------------------------------------------------------------
    def render_gl(self):
        """OpenGL 渲染一帧"""
        if not HAS_OPENGL:
            return

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()

        # 头部偏转
        glTranslatef(0.0, 0.0, -5.0)
        glRotatef(self.state.head_tilt_x * 15, 1.0, 0.0, 0.0)
        glRotatef(self.state.head_tilt_y * 15, 0.0, 1.0, 0.0)

        self._draw_face()
        self._draw_eyes()
        self._draw_mouth()
        self._draw_eyebrows()

    def _draw_face(self):
        """绘制面部轮廓"""
        glColor3f(1.0, 0.85, 0.75)  # 肤色
        glBegin(GL_TRIANGLE_FAN)
        glVertex2f(0.0, 0.0)
        for angle in np.linspace(0, 2 * math.pi, 40):
            glVertex2f(math.cos(angle) * 1.2, math.sin(angle) * 1.4)
        glEnd()

    def _draw_eyes(self):
        """绘制眼睛（含眨眼）"""
        blink = self.state.blink
        left_eye = (-0.35, 0.15)
        right_eye = (0.35, 0.15)
        eye_w, eye_h = 0.22, 0.18 * (1.0 - blink * 0.9)

        for (cx, cy) in [left_eye, right_eye]:
            # 眼白
            glColor3f(1.0, 1.0, 1.0)
            glBegin(GL_QUADS)
            glVertex2f(cx - eye_w, cy + eye_h)
            glVertex2f(cx + eye_w, cy + eye_h)
            glVertex2f(cx + eye_w, cy - eye_h)
            glVertex2f(cx - eye_w, cy - eye_h)
            glEnd()
            # 瞳孔
            glColor3f(0.1, 0.1, 0.2)
            gaze_offset_x = (self.state.gaze_x - 0.5) * 0.08
            gaze_offset_y = (self.state.gaze_y - 0.5) * 0.05
            r = 0.06 * (1.0 - blink)
            glBegin(GL_TRIANGLE_FAN)
            glVertex2f(cx + gaze_offset_x, cy + gaze_offset_y)
            for a in np.linspace(0, 2 * math.pi, 16):
                glVertex2f(cx + gaze_offset_x + math.cos(a) * r,
                           cy + gaze_offset_y + math.sin(a) * r)
            glEnd()

    def _draw_mouth(self):
        """绘制嘴（随唇形开合）"""
        openness = self.state.mouth_openness
        mouth_y = -0.4
        half_w = 0.35
        half_h = 0.04 + openness * 0.15

        glColor3f(0.7, 0.3, 0.3)  # 唇色
        glBegin(GL_QUADS)
        glVertex2f(-half_w, mouth_y + half_h)
        glVertex2f(half_w, mouth_y + half_h)
        glVertex2f(half_w, mouth_y - half_h)
        glVertex2f(-half_w, mouth_y - half_h)
        glEnd()

    def _draw_eyebrows(self):
        """绘制眉毛（情绪驱动）"""
        emotion_params = self.EMOTION_TO_LIVE2D.get(
            self.state.emotion, self.EMOTION_TO_LIVE2D[Emotion.NEUTRAL]
        )
        brow_offset = emotion_params["ParamBrow"] * 0.15
        brow_y = 0.42 + brow_offset

        glLineWidth(3.0)
        for side in [-1, 1]:
            cx = side * 0.3
            glColor3f(0.3, 0.2, 0.1)
            glBegin(GL_LINE_STRIP)
            glVertex2f(cx - 0.2, brow_y + side * 0.02)
            glVertex2f(cx, brow_y)
            glVertex2f(cx + 0.2, brow_y + side * 0.02)
            glEnd()

    # ------------------------------------------------------------
    # 表情参数导出（供 Live2D / 外部渲染器使用）
    # ------------------------------------------------------------
    def get_live2d_params(self) -> Dict[str, float]:
        """返回 Live2D 参数映射"""
        base = self.EMOTION_TO_LIVE2D.get(
            self.state.emotion, self.EMOTION_TO_LIVE2D[Emotion.NEUTRAL]
        )
        intensity = self.state.emotion_intensity
        return {
            k: v * intensity
            for k, v in base.items()
        } | {
            "ParamMouthOpen": self.state.mouth_openness,
            "ParamEyeBlink": self.state.blink,
        }