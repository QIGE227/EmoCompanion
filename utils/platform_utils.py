"""
平台适配工具 —— 检测运行环境，处理 Android/PC 差异
"""
import os
import sys
from pathlib import Path
from typing import Tuple

# ============================================================
# 平台检测
# ============================================================
_ANDROID = False
_LINUX = False
_WINDOWS = False

if hasattr(sys, 'getandroidapilevel'):
    _ANDROID = True
elif sys.platform == 'linux':
    _LINUX = True
elif sys.platform == 'win32':
    _WINDOWS = True


def is_android() -> bool:
    return _ANDROID

def is_pc() -> bool:
    return not _ANDROID

def platform_name() -> str:
    if _ANDROID:
        return "android"
    if _LINUX:
        return "linux"
    if _WINDOWS:
        return "windows"
    return "unknown"


# ============================================================
# 路径适配
# ============================================================
def get_data_dir() -> str:
    """数据目录（模型、配置等）"""
    if _ANDROID:
        # Android: 使用外部存储
        candidates = [
            "/sdcard/EmoCompanion",
            "/storage/emulated/0/EmoCompanion",
            os.path.join(os.environ.get("EXTERNAL_STORAGE", "/sdcard"), "EmoCompanion"),
        ]
        for d in candidates:
            if os.path.isdir(d):
                return d
        return candidates[0]
    else:
        return str(Path(__file__).parent.parent.resolve())


def get_models_dir() -> str:
    d = os.path.join(get_data_dir(), "models")
    os.makedirs(d, exist_ok=True)
    return d


def get_logs_dir() -> str:
    d = os.path.join(get_data_dir(), "logs")
    os.makedirs(d, exist_ok=True)
    return d


def get_assets_dir() -> str:
    d = os.path.join(get_data_dir(), "assets")
    os.makedirs(d, exist_ok=True)
    return d


# ============================================================
# 摄像头适配
# ============================================================
def get_camera_id() -> int:
    """返回前置摄像头 ID"""
    if _ANDROID:
        return 1   # Android 前置
    return 0       # PC 默认


def get_camera_backend() -> str:
    """返回摄像头后端"""
    if _ANDROID:
        return "android"
    return "opencv"


# ============================================================
# 权限适配
# ============================================================
def request_permissions():
    """请求运行时权限（仅 Android）"""
    if not _ANDROID:
        return True
    try:
        from android.permissions import request_permissions, Permission
        request_permissions([
            Permission.CAMERA,
            Permission.RECORD_AUDIO,
            Permission.WRITE_EXTERNAL_STORAGE,
            Permission.READ_EXTERNAL_STORAGE,
            Permission.INTERNET,
        ])
        return True
    except Exception as e:
        print(f"⚠ 权限请求失败: {e}")
        return False


# ============================================================
# 音频适配
# ============================================================
def get_audio_input_device() -> int | None:
    """返回音频输入设备ID"""
    if _ANDROID:
        return None  # 默认
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        for i, dev in enumerate(devices):
            if dev.get('max_input_channels', 0) > 0:
                return i
    except Exception:
        pass
    return None


def has_audio_output() -> bool:
    """是否有音频输出"""
    if _ANDROID:
        return True  # 所有 Android 设备都有
    try:
        import sounddevice as sd
        sd.query_devices()
        return True
    except Exception:
        return False


# ============================================================
# GPU / 性能
# ============================================================
def get_device() -> str:
    """推理设备选择"""
    if _ANDROID:
        return "cpu"   # 移动端统一用 CPU
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
        if torch.backends.mps.is_available():
            return "mps"
    except Exception:
        pass
    return "cpu"


def get_num_threads() -> int:
    """推荐线程数"""
    if _ANDROID:
        return 4   # 移动端保守
    return max(1, os.cpu_count() or 4)


# ============================================================
# 屏幕适配
# ============================================================
def get_screen_size() -> Tuple[int, int]:
    """返回 (宽, 高)"""
    if _ANDROID:
        try:
            from jnius import autoclass
            WindowManager = autoclass('android.view.WindowManager')
            # 简化：返回常见手机分辨率
            return 720, 1440
        except Exception:
            return 720, 1440
    return 480, 860   # PC 窗口默认