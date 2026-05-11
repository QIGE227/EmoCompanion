#!/usr/bin/env python3
"""
EmoCompanion 模型自动下载器
下载：Piper中文语音 / Whisper中文 / Qwen2 GGUF
"""
import os
import sys
import urllib.request
import hashlib
import json
from pathlib import Path

# 项目根
BASE = Path(os.environ.get("EMOCOMPANION_ROOT", "/sdcard/EmoCompanion"))
MODELS = BASE / "models"
MODELS.mkdir(parents=True, exist_ok=True)

# ============================================================
# 模型清单
# ============================================================
MODEL_LIST = {
    # ---- Piper 中文语音 ----
    "piper_zh": {
        "name": "Piper 中文语音 (huayan-medium)",
        "files": [
            {
                "url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/zh/zh_CN/huayan/medium/zh_CN-huayan-medium.onnx",
                "dest": str(MODELS / "piper_zh_CN" / "zh_CN-huayan-medium.onnx"),
                "sha256": None,  # 可选校验
            },
            {
                "url": "https://huggingface.co/rhasspy/piper-voices/resolve/main/zh/zh_CN/huayan/medium/zh_CN-huayan-medium.onnx.json",
                "dest": str(MODELS / "piper_zh_CN" / "zh_CN-huayan-medium.onnx.json"),
            },
        ],
        "size_mb": 54,
    },

    # ---- Whisper base (faster-whisper 自动缓存) ----
    "whisper_base": {
        "name": "Whisper base (中文优化)",
        "note": "faster-whisper 首次运行时自动从 HuggingFace 下载，约 140MB",
        "files": [],
        "auto": True,
    },

    # ---- Qwen2 7B GGUF ----
    "qwen2_7b": {
        "name": "Qwen2-7B-Instruct GGUF Q4_K_M",
        "note": "推荐手动下载到 models/ 目录",
        "urls": [
            "https://huggingface.co/Qwen/Qwen2-7B-Instruct-GGUF/resolve/main/qwen2-7b-instruct-q4_k_m.gguf",
        ],
        "dest": str(MODELS / "qwen2-7b-instruct-q4_k_m.gguf"),
        "size_mb": 4500,
    },

    # ---- MediaPipe (自动随 pip 安装) ----
    "mediapipe": {
        "name": "MediaPipe Face Mesh",
        "note": "pip install mediapipe 时自动安装，无需额外下载",
        "auto": True,
    },
}


def download_file(url: str, dest: str, desc: str = "") -> bool:
    """下载文件，带进度条"""
    os.makedirs(os.path.dirname(dest), exist_ok=True)

    # 已存在则跳过
    if os.path.exists(dest):
        size = os.path.getsize(dest)
        if size > 1000:
            print(f"  ✅ 已存在: {os.path.basename(dest)} ({size/1024/1024:.1f}MB)")
            return True

    print(f"  ⬇ 下载: {os.path.basename(dest)} ({desc})")
    try:
        def _progress(block_num, block_size, total_size):
            if total_size > 0:
                pct = min(block_num * block_size / total_size * 100, 100)
                downloaded = block_num * block_size / 1024 / 1024
                total = total_size / 1024 / 1024
                print(f"\r    {pct:.0f}% ({downloaded:.1f}/{total:.1f}MB)", end="")

        urllib.request.urlretrieve(url, dest, _progress)
        print()
        return True
    except Exception as e:
        print(f"\n  ❌ 失败: {e}")
        return False


def download_piper():
    """下载 Piper 中文语音模型"""
    info = MODEL_LIST["piper_zh"]
    print(f"\n📢 {info['name']} ({info['size_mb']}MB)")
    for f in info["files"]:
        download_file(f["url"], f["dest"], "Piper TTS 中文")


def check_whisper():
    """检查 Whisper 模型"""
    print(f"\n📢 Whisper base (首次运行自动下载 ~140MB)")
    cache_dir = os.path.expanduser("~/.cache/huggingface/hub")
    whisper_dir = os.path.join(cache_dir, "models--Systran--faster-whisper-base")
    if os.path.isdir(whisper_dir):
        print("  ✅ Whisper 模型已缓存")
    else:
        print("  ⚠ 未缓存，首次 ASR 加载时自动下载")


def print_qwen2_guide():
    """Qwen2 GGUF 下载指引"""
    info = MODEL_LIST["qwen2_7b"]
    print(f"\n📢 {info['name']} (~{info['size_mb']}MB)")
    dest = info["dest"]
    if os.path.exists(dest) and os.path.getsize(dest) > 100_000_000:
        print(f"  ✅ 已存在: {os.path.basename(dest)}")
    else:
        print(f"  ⚠ 需手动下载（文件太大，~4.5GB）:")
        print(f"    URL: {info['urls'][0]}")
        print(f"    保存到: {dest}")
        print(f"  💡 移动端推荐用 Qwen2-1.5B GGUF (~1GB)")
        print(f"    https://huggingface.co/Qwen/Qwen2-1.5B-Instruct-GGUF")


def main():
    print("=" * 60)
    print("  EmoCompanion 模型下载器")
    print("=" * 60)

    print("\n选择操作:")
    print("  1. 下载 Piper 中文语音 (54MB)")
    print("  2. 检查 Whisper 模型")
    print("  3. Qwen2 GGUF 下载指引")
    print("  4. 全部执行")
    print("  0. 退出")

    choice = input("\n输入: ").strip()

    if choice == "1" or choice == "4":
        download_piper()
        check_whisper()
        print_qwen2_guide()

    elif choice == "2":
        check_whisper()

    elif choice == "3":
        print_qwen2_guide()

    print("\n" + "=" * 60)
    print("  完成! 模型目录:", MODELS)
    pip_files = list(MODELS.glob("**/*.*"))
    for f in sorted(pip_files):
        size_mb = os.path.getsize(f) / 1024 / 1024
        print(f"    📄 {f.relative_to(MODELS)} ({size_mb:.1f}MB)")
    print("=" * 60)


if __name__ == "__main__":
    main()
