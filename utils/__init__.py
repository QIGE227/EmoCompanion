"""
工具模块：配置加载、日志、平台适配
"""
import yaml
import logging
import os
from pathlib import Path
from typing import Any, Dict

from utils.platform_utils import (
    is_android, is_pc, platform_name,
    get_data_dir, get_models_dir, get_logs_dir, get_assets_dir,
    get_camera_id, get_camera_backend, request_permissions,
    has_audio_output, get_device, get_num_threads, get_screen_size,
)

# ------------------------------------------------------------
# 项目根目录
# ------------------------------------------------------------
PROJECT_ROOT = get_data_dir()
os.makedirs(os.path.join(PROJECT_ROOT, "logs"), exist_ok=True)

# ------------------------------------------------------------
# 日志
# ------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(PROJECT_ROOT, "logs", "app.log"), encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("EmoCompanion")


def load_config(path: str = None) -> Dict[str, Any]:
    """加载 YAML 配置"""
    if path is None:
        path = os.path.join(PROJECT_ROOT, "config.yaml")
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    logger.info(f"配置已加载: {path} (平台: {platform_name()})")
    return cfg


# 全局单例
_config: Dict[str, Any] | None = None


def get_config() -> Dict[str, Any]:
    global _config
    if _config is None:
        _config = load_config()
    return _config
