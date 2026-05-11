"""
数字人显示组件 —— QOpenGLWidget
渲染数字人+表情+唇形
"""
from PyQt5.QtWidgets import QOpenGLWidget, QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QFont, QPixmap
import numpy as np

from core.emotion_recognizer import Emotion


class AvatarWidget(QWidget):
    """
    数字人显示组件
    - 优先使用 QOpenGLWidget 渲染
    - 若 OpenGL 不可用，回退到 QLabel + QPainter
    """

    # 信号：渲染帧就绪
    frame_ready = pyqtSignal()

    def __init__(self, parent=None, renderer=None):
        super().__init__(parent)
        self.renderer = renderer
        self._fps_counter = 0
        self._fps_timer = QTimer()
        self._fps_timer.timeout.connect(self._update_fps)

        self.setMinimumSize(360, 480)
        self.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #1a1a2e, stop:1 #16213e);
                border-radius: 16px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 情绪标签
        self.emotion_label = QLabel("😐 中性")
        self.emotion_label.setAlignment(Qt.AlignCenter)
        self.emotion_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 18px;
                font-weight: bold;
                background: rgba(0,0,0,0.3);
                border-radius: 20px;
                padding: 6px 20px;
            }
        """)
        self.emotion_label.setMaximumHeight(40)
        layout.addWidget(self.emotion_label, alignment=Qt.AlignTop | Qt.AlignHCenter)

        # OpenGL 尝试
        self._gl_widget = None
        self._fallback_label = QLabel("🎭\n数字人加载中...")
        self._fallback_label.setAlignment(Qt.AlignCenter)
        self._fallback_label.setStyleSheet("""
            QLabel {
                color: rgba(255,255,255,0.6);
                font-size: 48px;
            }
        """)
        layout.addWidget(self._fallback_label)

        self._init_gl()

    def _init_gl(self):
        """尝试初始化 OpenGL"""
        try:
            self._gl_widget = AvatarGLWidget(renderer=self.renderer)
            self.layout().replaceWidget(self._fallback_label, self._gl_widget)
            self._fallback_label.hide()
            self._gl_widget.show()
        except Exception:
            self._fallback_label.show()

    def set_emotion_display(self, emotion: Emotion, confidence: float):
        """更新情绪显示"""
        cn = emotion.cn_name
        emoji = emotion.emoji
        self.emotion_label.setText(f"{emoji} {cn} ({confidence:.0%})")

    def set_avatar_pixmap(self, pixmap):
        """回退模式：设置静态/序列帧"""
        self._fallback_label.setPixmap(pixmap)

    def _update_fps(self):
        self._fps_counter += 1

    def repaint_avatar(self):
        """强制刷新"""
        if self._gl_widget:
            self._gl_widget.update()
        self.update()


class AvatarGLWidget(QOpenGLWidget):
    """OpenGL 数字人渲染"""

    def __init__(self, parent=None, renderer=None):
        super().__init__(parent)
        self.renderer = renderer

    def initializeGL(self):
        glClearColor(0.1, 0.1, 0.18, 1.0)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    def resizeGL(self, w, h):
        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        aspect = w / max(h, 1)
        glOrtho(-2.0 * aspect, 2.0 * aspect, -2.0, 2.0, 0.1, 100.0)
        glMatrixMode(GL_MODELVIEW)

    def paintGL(self):
        if self.renderer:
            self.renderer.render_gl()