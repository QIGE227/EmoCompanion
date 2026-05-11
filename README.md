# EmoCompanion — 情感陪伴数字人

## 🎯 功能概览

| 功能 | 技术 | 状态 |
|------|------|------|
| 478点人脸检测 | MediaPipe Face Mesh | ✅ 框架完成 |
| 8种情绪识别 | ONNX + 启发式规则 | ✅ 框架完成 |
| 中文对话 | Qwen2 7B (4‑bit) | ✅ 框架完成 |
| 语音识别 | Whisper (faster-whisper) | ✅ 框架完成 |
| 语音合成 | Coqui TTS | ✅ 框架完成 |
| 数字人渲染 | OpenGL / Live2D | ✅ 框架完成 |
| 唇形同步 | 能量驱动 / Wav2Lip | ✅ 框架完成 |
| APK 打包 | Buildozer | ✅ 配置完成 |

## 📁 项目结构

```
EmoCompanion/
├── main.py                 # 主入口
├── config.yaml             # 全局配置
├── requirements.txt        # Python 依赖
├── buildozer.spec          # APK 打包配置
├── model_downloader.py     # 模型下载指南
├── core/
│   ├── face_detector.py    # MediaPipe 人脸检测
│   ├── emotion_recognizer.py # 情绪识别
│   ├── llm_engine.py       # Qwen2 对话引擎
│   ├── speech_recognizer.py # Whisper 语音识别
│   ├── speech_synthesizer.py # Coqui TTS 语音合成
│   ├── avatar_renderer.py  # 数字人渲染
│   └── lip_sync.py         # 唇形同步
├── ui/
│   ├── main_window.py      # 主窗口
│   ├── avatar_widget.py    # 数字人显示组件
│   └── chat_widget.py      # 聊天组件
├── models/                 # 模型文件目录
├── assets/                 # 资源文件
└── utils/                  # 工具模块
```

## 🚀 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 下载模型
```bash
python model_downloader.py   # 查看下载指南
```

### 3. 运行（PC 开发模式）
```bash
python main.py
```

### 4. 打包 APK
```bash
pip install buildozer
buildozer init                # 生成 buildozer.spec（已有则跳过）
buildozer android debug deploy run
```

## ⚙️ 配置说明

编辑 `config.yaml` 切换后端:

- **LLM**: `backend: transformers` → `backend: llama.cpp` (移动端推荐 GGUF)
- **ASR**: `model_size: base` (192MB) / `tiny` (72MB) / `small` (466MB)
- **TTS**: 可换用 PiperTTS 等更轻方案
- **Avatar**: `backend: opengl` → `backend: live2d` 需 Live2D Cubism SDK

## 📱 移动端优化建议

1. Qwen2 7B → GGUF Q4_K_M 量化 (~4GB)，用 llama.cpp 推理
2. Whisper → whisper.cpp GGML，极致轻量
3. TTS → PiperTTS (C++ 实现，< 50MB)
4. 情绪识别 → MediaPipe 关键点 + 轻量 ONNX (~5MB)
