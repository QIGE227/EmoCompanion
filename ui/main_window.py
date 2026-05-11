"""
主窗口 —— 情感陪伴数字人APP（管线集成版）
数字人（上半屏） + 聊天框（底部）
"""
import threading
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout,
    QLabel, QSystemTrayIcon,
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QCloseEvent

from utils import logger, get_config
from core import (
    Pipeline, PipelineState, Emotion,
)

from ui.avatar_widget import AvatarWidget
from ui.chat_widget import ChatWidget
from ui.splash_widget import SplashOverlay


class MainWindow(QMainWindow):
    """
    EmoCompanion 主界面
    ┌──────────────────────┐
    │  SplashOverlay (启动)│
    │  ├─ AvatarWidget     │ ~60%
    │  ├─ Divider          │
    │  └─ ChatWidget       │ ~40%
    └──────────────────────┘
    """

    def __init__(self):
        super().__init__()
        self.cfg = get_config()
        self.setWindowTitle(f"{self.cfg['app']['name']} v{self.cfg['app']['version']}")
        self.setMinimumSize(420, 720)
        self.resize(480, 860)

        # ---- 核心管线 ----
        self.pipeline = Pipeline()
        self._setup_pipeline_callbacks()

        # ---- UI ----
        self._setup_ui()
        self._connect_signals()

        # ---- 启动动画 ----
        self.splash_overlay.show()
        self.splash_overlay.start_loading()

        # ---- 异步初始化 ----
        self._load_step = 0
        self._load_messages = [
            "加载人脸检测引擎...",
            "加载情绪识别模型...",
            "加载数字人渲染器...",
            "加载语音合成引擎...",
            "加载语音识别引擎...",
            "加载唇形同步模块...",
            "加载大语言模型...",
        ]
        QTimer.singleShot(400, self._async_init_step)

        logger.info("MainWindow 初始化完成")

    # ============================================================
    # UI
    # ============================================================
    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        central.setStyleSheet("""
            QWidget {
                background: #0f0f1e;
                color: white;
                font-family: "Noto Sans CJK SC", "Microsoft YaHei", sans-serif;
            }
        """)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 状态栏
        self.status_label = QLabel("🚀 启动中...")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setMaximumHeight(26)
        self.status_label.setStyleSheet("""
            QLabel { background: rgba(0,0,0,0.5); color: #aaa; font-size: 11px; padding: 3px; }
        """)
        main_layout.addWidget(self.status_label)

        # 数字人区域 (叠层：AvatarWidget + SplashOverlay)
        self.avatar_widget = AvatarWidget(renderer=None)
        self.splash_overlay = SplashOverlay(parent=self)
        # Splash 覆盖在 avatar 上，加载完成后隐藏
        main_layout.addWidget(self.avatar_widget, stretch=6)

        # 分隔线
        divider = QLabel()
        divider.setMaximumHeight(2)
        divider.setStyleSheet("background: #333; margin: 0 12px;")
        main_layout.addWidget(divider)

        # 聊天区域
        self.chat_widget = ChatWidget()
        main_layout.addWidget(self.chat_widget, stretch=4)

    def _connect_signals(self):
        self.chat_widget.send_text.connect(self._on_user_send)
        self.chat_widget.voice_toggle.connect(self._on_voice_toggle)

    # ============================================================
    # 异步初始化
    # ============================================================
    def _async_init_step(self):
        """分步加载，每步更新启动画面"""
        if self._load_step >= len(self._load_messages):
            self._finish_loading()
            return

        msg = self._load_messages[self._load_step]
        progress = (self._load_step + 1) / len(self._load_messages)
        self.splash_overlay.update_status(msg, progress)

        def _load():
            try:
                self._do_step(self._load_step)
            except Exception as e:
                logger.error(f"加载步骤 {self._load_step} 失败: {e}")
            finally:
                self._load_step += 1
                QTimer.singleShot(200, self._async_init_step)

        threading.Thread(target=_load, daemon=True).start()

    def _do_step(self, step: int):
        """执行单个加载步骤"""
        if step == 0:
            self.pipeline.init_basic()
            self.avatar_widget.renderer = self.pipeline.avatar_renderer
            self.avatar_widget._init_gl()
        elif step == 1:
            pass  # 情绪识别已在 init_basic 完成
        elif step == 2:
            pass  # 数字人渲染已完成
        elif step == 3:
            self.pipeline.init_tts()
        elif step == 4:
            self.pipeline.init_asr()
        elif step == 5:
            pass  # 唇形同步已完成
        elif step == 6:
            self.pipeline.init_llm()

    def _finish_loading(self):
        """加载完成"""
        self.splash_overlay.finish_loading()
        QTimer.singleShot(600, lambda: self.splash_overlay.hide())
        self.status_label.setText("✅ 就绪 — 等待对话")

        # 启动管线
        self.pipeline.start()

        # 主循环刷新
        self._tick_timer = QTimer()
        self._tick_timer.timeout.connect(self._on_tick)
        self._tick_timer.start(33)

    # ============================================================
    # 管线回调
    # ============================================================
    def _setup_pipeline_callbacks(self):
        self.pipeline.on_emotion_change = self._on_emotion_change
        self.pipeline.on_state_change = self._on_pipeline_state
        self.pipeline.on_llm_response = self._on_llm_response
        self.pipeline.on_lipsync_update = self._on_lipsync

    def _on_emotion_change(self, emotion: Emotion, conf: float):
        self.avatar_widget.set_emotion_display(emotion, conf)

    def _on_pipeline_state(self, state: PipelineState):
        state_map = {
            PipelineState.IDLE: "✅ 就绪",
            PipelineState.LISTENING: "🎤 正在听...",
            PipelineState.THINKING: "🤔 思考中...",
            PipelineState.SPEAKING: "🔊 说话中...",
            PipelineState.ERROR: "⚠ 出错了",
        }
        self.status_label.setText(state_map.get(state, "…"))

    def _on_llm_response(self, text: str):
        self.chat_widget.add_message(
            text, is_user=False, emotion=self.pipeline.current_emotion
        )

    def _on_lipsync(self, openness: float):
        pass  # avatar 内部更新

    # ============================================================
    # 主循环
    # ============================================================
    def _on_tick(self):
        if self.pipeline.avatar_renderer:
            self.avatar_widget.repaint_avatar()

    # ============================================================
    # 用户交互
    # ============================================================
    def _on_user_send(self, text: str):
        self.chat_widget.add_message(text, is_user=True)
        self.pipeline.send_message(text)

    def _on_voice_toggle(self, enabled: bool):
        if enabled:
            self.pipeline.speech_recognizer.load()
            self.pipeline.speech_recognizer.start(
                callback=lambda t: self._on_asr_result(t)
            )
        else:
            self.pipeline.speech_recognizer.stop()

    def _on_asr_result(self, text: str):
        self.chat_widget.set_asr_text(text)
        # 自动发送
        QTimer.singleShot(100, lambda: self._on_user_send(text))

    # ============================================================
    # 生命周期
    # ============================================================
    def closeEvent(self, event: QCloseEvent):
        logger.info("正在关闭 EmoCompanion...")
        self.pipeline.shutdown()
        event.accept()