#!/usr/bin/env python3
"""
EmoCompanion — 情感陪伴数字人 APP
自动检测平台：PC端→PyQt5 | Android→Kivy
"""
import sys
import os
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import logger, get_config, is_android, platform_name, request_permissions


def run_pc():
    """PC 端：PyQt5 界面"""
    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtGui import QFont, QPalette, QColor
    from PyQt5.QtCore import Qt
    from ui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("EmoCompanion")

    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(15, 15, 30))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(25, 25, 50))
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(45, 45, 70))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.Highlight, QColor(74, 144, 217))
    app.setPalette(palette)
    font = QFont("Noto Sans CJK SC", 12)
    font.setStyleHint(QFont.SansSerif)
    app.setFont(font)

    window = MainWindow()
    window.show()
    logger.info("PC 模式已启动 (PyQt5)")
    sys.exit(app.exec_())


def run_android():
    """Android 端：Kivy 界面"""
    # 请求权限
    request_permissions()

    # 初始化核心模块（后台）
    from core.pipeline import Pipeline
    pipeline = Pipeline()

    def init_modules():
        logger.info("Android: 加载模块...")
        pipeline.init_basic()
        pipeline.init_tts()
        pipeline.init_asr()
        logger.info("Android: 基础模块就绪")

    threading.Thread(target=init_modules, daemon=True).start()

    # Kivy App
    from ui.app_android import EmoCompanionApp
    app = EmoCompanionApp(pipeline=pipeline)
    logger.info("Android 模式已启动 (Kivy)")
    app.run()


def main():
    logger.info("=" * 50)
    logger.info(f"EmoCompanion 启动 (平台: {platform_name()})")
    logger.info("=" * 50)

    try:
        cfg = get_config()
        logger.info(f"App: {cfg['app']['name']} v{cfg['app']['version']}")
    except Exception as e:
        logger.error(f"配置加载失败: {e}")
        sys.exit(1)

    if is_android():
        run_android()
    else:
        run_pc()


if __name__ == "__main__":
    main()