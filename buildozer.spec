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
requirements = python3,kivy==2.2.1,numpy,Pillow,opencv,mediapipe,onnxruntime,transformers,faster-whisper,piper-tts,pyyaml,soundfile,torch
# torch 在移动端用 CPU 版本

# ---- 权限 ----
android.permissions = INTERNET,CAMERA,RECORD_AUDIO,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,WAKE_LOCK,VIBRATE

# ---- 架构 ----
android.arch = arm64-v8a
android.minapi = 26
android.ndk = 25c
android.sdk = 33

# ---- 打包选项 ----
android.allow_backup = True
android.fullscreen = 1
android.orientation = portrait
android.presplash_color = #0f0f1e
android.wakelock = True

# Kivy 引导
android.bootstraps = sdl2
android.add_activity = org.kivy.android.PythonActivity

# 额外 Java 依赖
android.gradle_dependencies = androidx.camera:camera-core:1.1.0, androidx.camera:camera-camera2:1.1.0, androidx.camera:camera-lifecycle:1.1.0

# 日志
log_level = 1
warn_on_root = 1

[buildozer]
log_level = 2
