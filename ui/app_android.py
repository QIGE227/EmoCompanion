"""
EmoCompanion Android App — Kivy 主界面
"""
import threading
import time
from typing import Optional

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.progressbar import ProgressBar
from kivy.uix.image import Image
from kivy.uix.camera import Camera as KivyCamera
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle, RoundedRectangle, Line, Ellipse
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.utils import platform as kivy_platform

from utils import logger, get_config
from core.emotion_recognizer import Emotion


class AvatarCanvas(FloatLayout):
    """数字人渲染区域（Kivy Canvas）"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.emotion = Emotion.NEUTRAL
        self.mouth_open = 0.0
        self.blink = 0.0
        self.emotion_conf = 0.0

        with self.canvas:
            Color(0.1, 0.1, 0.18)
            self.bg = Rectangle(pos=self.pos, size=self.size)

        self.bind(pos=self._update, size=self._update)

    def _update(self, *args):
        self.bg.pos = self.pos
        self.bg.size = self.size
        self._draw_face()

    def set_emotion(self, emotion: Emotion, conf: float):
        self.emotion = emotion
        self.emotion_conf = conf
        self._draw_face()

    def set_mouth(self, openness: float):
        self.mouth_open = min(openness, 1.0)
        self._draw_face()

    def _draw_face(self):
        """Kivy Canvas 绘制数字人面部"""
        self.canvas.after.clear()
        w, h = self.width, self.height
        cx, cy = w / 2, h * 0.55
        r = min(w, h) * 0.35

        with self.canvas.after:
            # 肤色圆脸
            Color(1.0, 0.85, 0.75)
            Ellipse(pos=(cx - r, cy - r * 1.1), size=(r * 2, r * 2.2))

            # 眼睛
            eye_y = cy + r * 0.18
            eye_r = r * 0.12
            blink = self.blink

            for ex in [cx - r * 0.35, cx + r * 0.35]:
                Color(1, 1, 1)
                if blink < 0.9:
                    Ellipse(pos=(ex - eye_r, eye_y - eye_r * (1 - blink)),
                            size=(eye_r * 2, eye_r * 2 * (1 - blink)))
                Color(0.1, 0.1, 0.2)
                if blink < 0.5:
                    pr = eye_r * 0.5
                    Ellipse(pos=(ex - pr, eye_y - pr),
                            size=(pr * 2, pr * 2))

            # 嘴巴
            mouth_y = cy - r * 0.4
            mw = r * 0.45
            mh = r * 0.05 + self.mouth_open * r * 0.15
            Color(0.75, 0.3, 0.3)
            Ellipse(pos=(cx - mw, mouth_y - mh), size=(mw * 2, mh * 2))

            # 情绪标签
            if self.emotion:
                Color(1, 1, 1, 0.8)


class ChatBubble(BoxLayout):
    """聊天气泡"""

    def __init__(self, text: str, is_user: bool, emotion: Emotion = None, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.padding = dp(8)
        self.size_hint_y = None

        emoji = emotion.emoji if emotion else ""
        prefix = "👤 " if is_user else f"🤖{emoji} "

        label = Label(
            text=f"{prefix}{text}",
            color=(1, 1, 1, 1),
            size_hint_y=None,
            text_size=(dp(300), None),
            halign='left',
            valign='top',
            padding=dp(10),
        )
        label.bind(texture_size=label.setter('size'))
        self.add_widget(label)

        # 背景色
        with self.canvas.before:
            color = (0.18, 0.42, 0.31, 1) if is_user else (0.23, 0.23, 0.36, 1)
            Color(*color)
            self.rect = RoundedRectangle(radius=[dp(12)], size=label.size, pos=label.pos)
        label.bind(size=self._update_rect, pos=self._update_rect)

    def _update_rect(self, instance, value):
        self.rect.size = instance.size
        self.rect.pos = instance.pos


class EmoCompanionApp(App):
    """情感陪伴数字人 Kivy App"""

    def __init__(self, pipeline=None, **kwargs):
        super().__init__(**kwargs)
        self.pipeline = pipeline
        self.chat_messages = []
        self.is_voice_mode = False
        self._loading_step = 0

    def build(self):
        self.title = "EmoCompanion"
        Window.clearcolor = (0.06, 0.06, 0.12, 1)

        # 根布局
        self.root = BoxLayout(orientation='vertical', spacing=dp(4), padding=dp(8))

        # === 状态栏 ===
        self.status_bar = Label(
            text="🚀 初始化中...",
            size_hint_y=None,
            height=dp(26),
            color=(0.6, 0.6, 0.7, 1),
            font_size=dp(12),
        )
        self.root.add_widget(self.status_bar)

        # === 数字人区域 ===
        self.avatar = AvatarCanvas(size_hint=(1, 0.55))
        self.root.add_widget(self.avatar)

        # 进度条（加载期可见）
        self.progress = ProgressBar(
            max=100, value=0,
            size_hint_y=None, height=dp(6),
            background_color=(0.2, 0.2, 0.3, 1),
        )
        self.root.add_widget(self.progress)

        # === 聊天区域 ===
        self.chat_scroll = ScrollView(size_hint=(1, 0.3))
        self.chat_layout = BoxLayout(orientation='vertical', spacing=dp(4),
                                      size_hint_y=None, padding=dp(4))
        self.chat_layout.bind(minimum_height=self.chat_layout.setter('height'))
        self.chat_scroll.add_widget(self.chat_layout)
        self.root.add_widget(self.chat_scroll)

        # === 输入区域 ===
        input_bar = BoxLayout(orientation='horizontal', size_hint_y=None,
                               height=dp(48), spacing=dp(6))

        self.voice_btn = Button(
            text="🎤", size_hint_x=None, width=dp(44),
            background_color=(0.23, 0.23, 0.36, 1),
        )
        self.voice_btn.bind(on_press=self._on_voice)
        input_bar.add_widget(self.voice_btn)

        self.input_box = TextInput(
            hint_text="输入消息...",
            multiline=False,
            background_color=(0.16, 0.16, 0.29, 1),
            foreground_color=(1, 1, 1, 1),
            cursor_color=(1, 1, 1, 1),
            padding=dp(10),
        )
        self.input_box.bind(on_text_validate=self._on_send)
        input_bar.add_widget(self.input_box)

        send_btn = Button(
            text="发送", size_hint_x=None, width=dp(56),
            background_color=(0.29, 0.56, 0.85, 1),
        )
        send_btn.bind(on_press=self._on_send)
        input_bar.add_widget(send_btn)

        self.root.add_widget(input_bar)

        # 启动加载
        Clock.schedule_once(lambda dt: self._start_loading(), 0.5)
        return self.root

    # ============================================================
    # 加载流程
    # ============================================================
    def _start_loading(self):
        steps = [
            "加载人脸检测引擎...",
            "加载情绪识别模型...",
            "加载数字人渲染器...",
            "加载语音合成...",
            "加载语音识别...",
            "加载唇形同步...",
            "加载大语言模型...",
        ]
        self._total_steps = len(steps)

        def _load_step(i):
            if i >= self._total_steps:
                self._finish_loading()
                return
            self.status_bar.text = f"⏳ {steps[i]}"
            self.progress.value = (i + 1) / self._total_steps * 100

            def _do():
                try:
                    if i == 0 and self.pipeline:
                        self.pipeline.init_basic()
                    elif i == 3 and self.pipeline:
                        self.pipeline.init_tts()
                    elif i == 4 and self.pipeline:
                        self.pipeline.init_asr()
                    elif i == 6 and self.pipeline:
                        self.pipeline.init_llm()
                except Exception as e:
                    logger.error(f"加载步骤{i}失败: {e}")
                finally:
                    Clock.schedule_once(lambda dt, j=i+1: _load_step(j), 0.3)

            threading.Thread(target=_do, daemon=True).start()

        _load_step(0)

    def _finish_loading(self):
        self.status_bar.text = "✅ 就绪 — 等待对话"
        self.progress.value = 100
        # 隐藏进度条
        Clock.schedule_once(lambda dt: setattr(self.progress, 'opacity', 0), 1.5)

        if self.pipeline:
            self.pipeline.start()

        # 数字人定时刷新
        Clock.schedule_interval(self._update_avatar, 1.0 / 30.0)

    # ============================================================
    # UI 更新
    # ============================================================
    def _update_avatar(self, dt):
        if self.pipeline and self.pipeline.avatar_renderer:
            self.pipeline.avatar_renderer.tick(dt)
            self.avatar.set_emotion(
                self.pipeline.current_emotion,
                self.pipeline.latest_frame.emotion_conf,
            )

    def _add_chat(self, text: str, is_user: bool, emotion: Emotion = None):
        bubble = ChatBubble(text=text, is_user=is_user, emotion=emotion)
        self.chat_layout.add_widget(bubble)
        self.chat_scroll.scroll_y = 0

    # ============================================================
    # 事件处理
    # ============================================================
    def _on_send(self, instance):
        text = self.input_box.text.strip()
        if not text:
            return
        self._add_chat(text, is_user=True)
        self.input_box.text = ""

        if self.pipeline:
            self.pipeline.send_message(text)

            def _get_response():
                time.sleep(0.5)  # 等待 pipeline 处理
                # 从 pipeline 取最新 AI 回复
                if self.pipeline.chat_history:
                    last = self.pipeline.chat_history[-1]
                    if last[0] == "ai":
                        Clock.schedule_once(
                            lambda dt, t=last[1], e=self.pipeline.current_emotion:
                            self._add_chat(t, is_user=False, emotion=e)
                        )

            threading.Thread(target=_get_response, daemon=True).start()

    def _on_voice(self, instance):
        self.is_voice_mode = not self.is_voice_mode
        if self.is_voice_mode:
            self.voice_btn.text = "🔴"
            self.status_bar.text = "🎤 正在听..."
            if self.pipeline and self.pipeline.speech_recognizer:
                self.pipeline.speech_recognizer.load()
                self.pipeline.speech_recognizer.start(
                    callback=lambda t: Clock.schedule_once(
                        lambda dt, text=t: self._on_asr(text)
                    )
                )
        else:
            self.voice_btn.text = "🎤"
            self.status_bar.text = "✅ 就绪"
            if self.pipeline and self.pipeline.speech_recognizer:
                self.pipeline.speech_recognizer.stop()

    def _on_asr(self, text: str):
        self.input_box.text = text
        self._on_send(None)

    def on_pause(self):
        """Android 进入后台"""
        if self.pipeline:
            self.pipeline.stop()
        return True

    def on_resume(self):
        """Android 恢复"""
        if self.pipeline:
            self.pipeline.start()

    def on_stop(self):
        """App 退出"""
        if self.pipeline:
            self.pipeline.shutdown()