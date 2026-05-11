"""
聊天组件 —— 底部对话区域
包含：消息列表 + 输入框 + 语音按钮
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QLabel, QScrollArea, QSizePolicy,
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QColor, QTextCursor
from datetime import datetime
from core.emotion_recognizer import Emotion


class ChatBubble(QWidget):
    """聊天气泡"""

    def __init__(self, text: str, is_user: bool, emotion: Emotion = None):
        super().__init__()
        self.text = text
        self.is_user = is_user
        self.emotion = emotion

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        # 气泡
        self.bubble_label = QLabel(text)
        self.bubble_label.setWordWrap(True)
        self.bubble_label.setMaximumWidth(300)
        self.bubble_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)

        align = "right" if is_user else "left"
        color = "#2d6a4f" if is_user else "#3a3a5c"
        emoji = f"{emotion.emoji} " if emotion else ""

        self.bubble_label.setStyleSheet(f"""
            QLabel {{
                background: {color};
                color: white;
                border-radius: 14px;
                padding: 10px 14px;
                font-size: 14px;
            }}
        """)
        self.bubble_label.setAlignment(Qt.AlignLeft)

        layout.addWidget(self.bubble_label, alignment=(
            Qt.AlignRight if is_user else Qt.AlignLeft
        ))


class ChatWidget(QWidget):
    """
    聊天组件
    - 对话气泡列表
    - 底部输入框 + 发送/语音按钮
    """

    send_text = pyqtSignal(str)          # 发送文本
    voice_toggle = pyqtSignal(bool)      # 语音开关 (True=开始, False=停止)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMaximumHeight(320)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ---- 消息滚动区 ----
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background: rgba(15, 15, 30, 0.8);
                border: none;
                border-radius: 12px 12px 0 0;
            }
            QScrollBar:vertical {
                width: 6px;
                background: transparent;
            }
            QScrollBar::handle:vertical {
                background: rgba(255,255,255,0.2);
                border-radius: 3px;
            }
        """)

        self.message_container = QWidget()
        self.message_layout = QVBoxLayout(self.message_container)
        self.message_layout.setAlignment(Qt.AlignTop)
        self.message_layout.setSpacing(8)
        self.message_layout.addStretch()

        self.scroll_area.setWidget(self.message_container)
        main_layout.addWidget(self.scroll_area)

        # ---- 输入区域 ----
        input_row = QHBoxLayout()
        input_row.setContentsMargins(8, 8, 8, 8)
        input_row.setSpacing(8)

        # 语音按钮
        self.voice_btn = QPushButton("🎤")
        self.voice_btn.setFixedSize(42, 42)
        self.voice_btn.setCheckable(True)
        self.voice_btn.setStyleSheet("""
            QPushButton {
                background: #3a3a5c;
                color: white;
                border-radius: 21px;
                font-size: 20px;
                border: none;
            }
            QPushButton:checked {
                background: #e63946;
            }
        """)
        self.voice_btn.clicked.connect(self._on_voice_click)
        input_row.addWidget(self.voice_btn)

        # 输入框
        self.input_edit = QTextEdit()
        self.input_edit.setPlaceholderText("输入消息... 或按语音按钮说话")
        self.input_edit.setMaximumHeight(80)
        self.input_edit.setMinimumHeight(40)
        self.input_edit.setStyleSheet("""
            QTextEdit {
                background: #2a2a4a;
                color: white;
                border: 1px solid #444;
                border-radius: 20px;
                padding: 8px 14px;
                font-size: 14px;
            }
        """)
        self.input_edit.setAcceptRichText(False)
        input_row.addWidget(self.input_edit)

        # 发送按钮
        self.send_btn = QPushButton("发送")
        self.send_btn.setFixedSize(56, 42)
        self.send_btn.setStyleSheet("""
            QPushButton {
                background: #4a90d9;
                color: white;
                border-radius: 21px;
                font-size: 14px;
                font-weight: bold;
                border: none;
            }
            QPushButton:pressed {
                background: #357abd;
            }
        """)
        self.send_btn.clicked.connect(self._on_send)
        input_row.addWidget(self.send_btn)

        # 输入框回车键发送
        self.input_edit.installEventFilter(self)

        main_layout.addLayout(input_row)

    # ------------------------------------------------------------
    # 公开接口
    # ------------------------------------------------------------
    def add_message(self, text: str, is_user: bool,
                    emotion: Emotion = None):
        """添加消息气泡"""
        bubble = ChatBubble(text, is_user, emotion)
        self.message_layout.insertWidget(
            self.message_layout.count() - 1, bubble
        )
        # 自动滚动到底部
        QTimer.singleShot(50, self._scroll_to_bottom)

    def set_voice_state(self, active: bool):
        """更新语音按钮状态"""
        self.voice_btn.setChecked(active)
        self.voice_btn.setText("🔴" if active else "🎤")

    def set_asr_text(self, text: str):
        """语音识别结果填入输入框"""
        self.input_edit.setText(text)

    # ------------------------------------------------------------
    # 内部逻辑
    # ------------------------------------------------------------
    def _on_send(self):
        text = self.input_edit.toPlainText().strip()
        if not text:
            return
        self.add_message(text, is_user=True)
        self.input_edit.clear()
        self.send_text.emit(text)

    def _on_voice_click(self, checked: bool):
        self.voice_toggle.emit(checked)
        self.set_voice_state(checked)

    def _scroll_to_bottom(self):
        sb = self.scroll_area.verticalScrollBar()
        sb.setValue(sb.maximum())

    def eventFilter(self, obj, event):
        """按 Enter 发送（Shift+Enter 换行）"""
        from PyQt5.QtCore import QEvent
        if obj == self.input_edit and event.type() == QEvent.KeyPress:
            if (event.key() == Qt.Key_Return and
                    not event.modifiers() & Qt.ShiftModifier):
                self._on_send()
                return True
        return super().eventFilter(obj, event)