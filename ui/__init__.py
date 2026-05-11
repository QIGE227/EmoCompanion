"""
UI 模块 — PC (PyQt5) + Android (Kivy)
"""
from ui.main_window import MainWindow
from ui.avatar_widget import AvatarWidget, AvatarGLWidget
from ui.chat_widget import ChatWidget, ChatBubble
from ui.splash_widget import SplashOverlay

# Android Kivy UI — 仅在 Android 环境下导入
try:
    from ui.app_android import EmoCompanionApp
except ImportError:
    EmoCompanionApp = None
