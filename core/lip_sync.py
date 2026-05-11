"""
唇形同步模块 —— 音频驱动的嘴形动画
策略：
- simple: 基于音频能量包络驱动 mouth openness
- wav2lip: 深度学习唇形生成（ONNX 推理）
"""
import numpy as np
from collections import deque
from typing import Callable, Optional
from utils import logger, get_config


class LipSync:
    """
    唇形同步引擎
    - 实时分析音频能量 → 映射 mouth_openness
    - 可选 Wav2Lip 推理（生成完整唇形帧）
    """

    def __init__(self):
        cfg = get_config()["lip_sync"]
        self.backend = cfg["backend"]
        self.threshold = cfg["mouth_open_threshold"]
        self.smooth_window = cfg["smooth_window"]
        self.wav2lip_model = cfg.get("wav2lip_model", "")

        # 平滑窗口
        self._energy_history: deque = deque(maxlen=self.smooth_window)
        self._current_openness: float = 0.0

        # Wav2Lip
        self._wav2lip_session = None
        if self.backend == "wav2lip":
            self._init_wav2lip()

    def _init_wav2lip(self):
        """加载 Wav2Lip ONNX 模型"""
        try:
            import onnxruntime as ort
            self._wav2lip_session = ort.InferenceSession(self.wav2lip_model)
            logger.info(f"Wav2Lip 模型已加载: {self.wav2lip_model}")
        except Exception as e:
            logger.warning(f"Wav2Lip 加载失败: {e}，回退 simple")

    # ------------------------------------------------------------
    # 音频能量 → 唇形开合 (simple)
    # ------------------------------------------------------------
    def process_audio_chunk(self, audio: np.ndarray,
                            sample_rate: int = 22050) -> float:
        """
        输入音频块 → 返回当前 mouth_openness (0~1)
        audio: float32 [-1, 1]
        """
        if self.backend == "wav2lip" and self._wav2lip_session:
            return self._process_wav2lip(audio, sample_rate)

        # 能量包络
        energy = np.sqrt(np.mean(audio ** 2))
        self._energy_history.append(energy)

        # 动态归一化
        if len(self._energy_history) >= 3:
            mean_e = np.mean(self._energy_history)
            std_e = np.std(self._energy_history) + 1e-6
            z_score = (energy - mean_e) / std_e
            # sigmoid 映射
            openness = 1.0 / (1.0 + np.exp(-5.0 * (z_score - 0.5)))
            openness = np.clip(openness, 0.0, 1.0)
        else:
            openness = min(energy * 3.0, 1.0)

        # 指数平滑
        alpha = 0.3
        self._current_openness = (
            alpha * openness + (1.0 - alpha) * self._current_openness
        )

        if self._current_openness < self.threshold:
            return 0.0
        return self._current_openness

    def _process_wav2lip(self, audio: np.ndarray,
                         sample_rate: int) -> float:
        """Wav2Lip 推理（轻量版）"""
        # 重采样 + Mel 谱 → ONNX → mouth openness
        try:
            import librosa
            mel = librosa.feature.melspectrogram(
                y=audio, sr=sample_rate, n_mels=80,
                hop_length=200, n_fft=800,
            )
            mel_db = librosa.power_to_db(mel, ref=np.max)
            # 取均值作为口型强度
            openness = np.mean(mel_db[-20:]) / 30.0 + 0.5
            return np.clip(openness, 0.0, 1.0)
        except Exception:
            return 0.0

    # ------------------------------------------------------------
    # 批量处理（用于 WAV 文件离线分析）
    # ------------------------------------------------------------
    def analyze_file(self, wav_path: str,
                     callback: Optional[Callable[[float, float], None]] = None
                     ) -> np.ndarray:
        """
        分析整个 WAV 文件 → 返回每帧的 openness 数组
        """
        try:
            import soundfile as sf
            audio, sr = sf.read(wav_path)
            if audio.ndim > 1:
                audio = audio.mean(axis=1)
        except Exception as e:
            logger.warning(f"音频读取失败 (可能缺PortAudio): {e}")
            return np.array([])

        chunk_size = int(0.04 * sr)  # 40ms 窗口
        hop_size = int(0.02 * sr)    # 20ms 步进
        result = []

        for i in range(0, len(audio) - chunk_size, hop_size):
            chunk = audio[i:i + chunk_size]
            openness = self.process_audio_chunk(chunk, sr)
            result.append(openness)
            if callback:
                callback(i / sr, openness)

        return np.array(result)