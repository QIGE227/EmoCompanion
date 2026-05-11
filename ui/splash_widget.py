"""
启动加载画面 —— 半透明覆盖层，带进度条和动画
"""
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QPoint
from PyQt5.QtGui import QFont, QColor, QPainter, QLinearGradient, QBrush


class SplashOverlay(QWidget):
    """
    启动画覆盖层
    - 渐变背景 + Logo + 进度条
    - 脉冲动画
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)

        # 覆盖父窗口
        if parent:
            self.setGeometry(parent.rect())
            parent.installEventFilter(self)

        self.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0d0d1a, stop:0.5 #1a1a2e, stop:1 #0d0d1a);
            }
        """)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(20)

        # Logo / 标题
        self.logo_label = QLabel("🎭")
        self.logo_label.setAlignment(Qt.AlignCenter)
        self.logo_label.setStyleSheet("""
            QLabel {
                background: transparent;
                font-size: 72px;
            }
        """)
        layout.addWidget(self.logo_label)

        self.title_label = QLabel("EmoCompanion")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("""
            QLabel {
                background: transparent;
                color: #e0e0ff;
                font-size: 28px;
                font-weight: bold;
                letter-spacing: 4px;
            }
        """)
        layout.addWidget(self.title_label)

        self.subtitle_label = QLabel("情感陪伴数字人")
        self.subtitle_label.setAlignment(Qt.AlignCenter)
        self.subtitle_label.setStyleSheet("""
            QLabel {
                background: transparent;
                color: #8888bb;
                font-size: 14px;
            }
        """)
        layout.addWidget(self.subtitle_label)

        # 间距
        spacer = QLabel()
        spacer.setFixedHeight(30)
        spacer.setStyleSheet("background: transparent;")
        layout.addWidget(spacer)

        # 状态文字
        self.status_label = QLabel("正在初始化...")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("""
            QLabel {
                background: transparent;
                color: #aaa;
                font-size: 13px;
            }
        """)
        layout.addWidget(self.status_label)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedWidth(260)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background: rgba(255,255,255,0.08);
                border: none;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4a90d9, stop:1 #7c5cbf);
                border-radius: 3px;
            }
        """)
        # 居中放置
        progress_wrapper = QWidget()
        progress_wrapper.setStyleSheet("background: transparent;")
        pw_layout = QVBoxLayout(progress_wrapper)
        pw_layout.setAlignment(Qt.AlignCenter)
        pw_layout.addWidget(self.progress_bar)
        layout.addWidget(progress_wrapper)

        # 脉冲动画
        self._pulse_anim: QPropertyAnimation | None = None

    # ------------------------------------------------------------
    # 公开接口
    # ------------------------------------------------------------
    def start_loading(self):
        """显示并开始动画"""
        self.show()
        self.raise_()
        self._start_pulse()

    def update_status(self, text: str, progress: float):
        """更新加载状态"""
        self.status_label.setText(text)
        self.progress_bar.setValue(int(progress * 100))

    def finish_loading(self):
        """加载完成"""
        self.status_label.setText("✅ 加载完成")
        self.progress_bar.setValue(100)
        self._stop_pulse()

    # ------------------------------------------------------------
    # 脉冲动画
    # ------------------------------------------------------------
    def _start_pulse(self):
        """Logo 脉冲动画"""
        self._pulse_anim = QPropertyAnimation(self.logo_label, b"pos")
        self._pulse_anim.setDuration(1200)
        self._pulse_anim.setLoopCount(-1)  # 无限循环
        self._pulse_anim.setEasingCurve(QEasingCurve.InOutSine)

        base_y = self.logo_label.y()
        self._pulse_anim.setKeyValueAt(0.0, QPoint(self.logo_label.x(), base_y))
        self._pulse_anim.setKeyValueAt(0.5, QPoint(self.logo_label.x(), base_y - 8))
        self._pulse_anim.setKeyValueAt(1.0, QPoint(self.logo_label.x(), base_y))
        self._pulse_anim.start()

    def _stop_pulse(self):
        if self._pulse_anim:
            self._pulse_anim.stop()
            self._pulse_anim = None

    # ------------------------------------------------------------
    # 事件
    # ------------------------------------------------------------
    def eventFilter(self, obj, event):
        """跟随父窗口 resize"""
        from PyQt5.QtCore import QEvent
        if event.type() == QEvent.Resize and obj == self.parent():
            self.setGeometry(obj.rect())
        return super().eventFilter(obj, event)