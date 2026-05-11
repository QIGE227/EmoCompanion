[app]
# ============================================================
# Buildozer 配置 —— EmoCompanion APK
# ============================================================

title = EmoCompanion
package.name = emocompanion
package.domain = com.emocompanion

source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf,otf,wav,mp3,ogg,json,yaml,onnx,bin,gguf
version = 0.1.0

# ---- 依赖 ----
# 一期轻量方案：本地运行 MediaPipe + 情绪识别 + Piper TTS + OpenGL 渲染
# LLM / ASR 通过云端 API 或用户手动下载 GGUF 模型加载
# torch / transformers / faster-whisper 无法通过 p4a 编译，已移除
requirements = python3,kivy==2.2.1,numpy,Pillow,opencv,mediapipe,pyyaml,soundfile,requests,android

# ---- 权限 ----
android.permissions = INTERNET,CAMERA,RECORD_AUDIO,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,WAKE_LOCK,VIBRATE

# ---- 架构 ----
android.arch = arm64-v8a
android.minapi = 26
android.ndk = 25.2.9519653
android.sdk = 33

# ---- 打包选项 ----
android.allow_backup = True
android.fullscreen = 1
android.orientation = portrait
android.presplash_color = #0f0f1e
android.wakelock = True

# Kivy 引导
android.bootstrap = sdl2
# android.add_activity 一般无需手动指定，buildozer 自动处理

# 额外 Java 依赖（CameraX 用于前置摄像头）
android.gradle_dependencies = androidx.camera:camera-core:1.1.0, androidx.camera:camera-camera2:1.1.0, androidx.camera:camera-lifecycle:1.1.0

# 日志
log_level = 1
warn_on_root = 1

[buildozer]
log_level = 2
