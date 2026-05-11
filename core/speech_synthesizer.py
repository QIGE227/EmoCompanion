"""
语音合成模块 —— Coqui TTS
文字 → 语音 WAV，支持流式播放
"""
import io
import tempfile
import threading
from typing import Optional, Callable
from utils import logger, get_config

# ---- 安全导入音频库 ----
HAS_SOUND = False
try:
    import sounddevice as sd
    import soundfile as sf
    # 验证 PortAudio 库可用
    sd.query_devices()
    HAS_SOUND = True
except Exception:
    sd = None
    sf = None
    logger.warning("sounddevice/soundfile 不可用 (PortAudio未安装或无音频设备)")


class SpeechSynthesizer:
    """
    Coqui TTS 封装
    - 支持多种中文模型
    - 可切换说话人
    """

    def __init__(self):
        cfg = get_config()["tts"]
        self.backend = cfg["backend"]
        self.model_name = cfg["model_name"]
        self.speaker_wav = cfg["speaker_wav"]
        self.speed = cfg["speed"]
        self.use_gpu = cfg["use_gpu"]

        self.tts_model = None
        self._lock = threading.Lock()
        self._piper_voice = None      # Piper 后端

    def load(self) -> bool:
        """加载 TTS 模型"""
        logger.info(f"正在加载 TTS: {self.model_name} (backend={self.backend})...")
        if self.backend == "piper":
            return self._load_piper()
        return self._load_coqui()

    def _load_coqui(self) -> bool:
        try:
            from TTS.api import TTS
            self.tts_model = TTS(model_name=self.model_name, gpu=self.use_gpu)
            logger.info(f"Coqui TTS 已加载: {self.model_name}")
            return True
        except Exception as e:
            logger.warning(f"Coqui TTS 加载失败: {e}，尝试 Piper")
            return self._load_piper()

    def _load_piper(self) -> bool:
        """加载 Piper TTS 模型（轻量，适合移动端）"""
        try:
            import piper
            # Piper 默认模型路径: ~/.config/piper/voices/
            model_path = f"models/piper_zh_CN/zh_CN-{self.speaker_wav or 'default'}.onnx"
            config_path = model_path.replace(".onnx", ".json")
            import os
            if not os.path.exists(model_path):
                logger.warning(f"Piper 模型未找到: {model_path}")
                logger.info("下载: pip install piper-tts && python -m piper download zh_CN")
                return False
            self._piper_voice = piper.PiperVoice.load(model_path, config_path=config_path)
            logger.info(f"Piper TTS 已加载: {model_path}")
            return True
        except Exception as e:
            logger.error(f"Piper TTS 加载失败: {e}")
            return False

    # ------------------------------------------------------------
    # 合成接口
    # ------------------------------------------------------------
    def synthesize(self, text: str) -> Optional[bytes]:
        """
        将文字合成为 WAV 字节流
        """
        if self._piper_voice:
            return self._synthesize_piper(text)
        if self.tts_model:
            return self._synthesize_coqui(text)
        logger.error("TTS 模型未加载")
        return None

    def _synthesize_coqui(self, text: str) -> Optional[bytes]:
        with self._lock:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                out_path = f.name
            try:
                self.tts_model.tts_to_file(text=text, file_path=out_path, speed=self.speed)
                with open(out_path, "rb") as f:
                    wav_bytes = f.read()
                import os
                os.unlink(out_path)
                return wav_bytes
            except Exception as e:
                logger.error(f"Coqui TTS 合成失败: {e}")
                return None

    def _synthesize_piper(self, text: str) -> Optional[bytes]:
        """Piper TTS 合成"""
        with self._lock:
            try:
                audio = b""
                for chunk in self._piper_voice.synthesize_stream_raw(text):
                    audio += chunk
                # 包装为 WAV
                import io as _io
                import wave
                buf = _io.BytesIO()
                with wave.open(buf, 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)  # 16-bit
                    wf.setframerate(22050)
                    wf.writeframes(audio)
                return buf.getvalue()
            except Exception as e:
                logger.error(f"Piper TTS 合成失败: {e}")
                return None

    def speak(self, text: str, blocking: bool = False):
        """
        直接播放合成语音
        """
        if not HAS_SOUND:
            logger.warning("音频播放不可用")
            return

        wav_bytes = self.synthesize(text)
        if wav_bytes is None:
            return

        data, sr = sf.read(io.BytesIO(wav_bytes))
        sd.play(data, sr)
        if blocking:
            sd.wait()

    def synthesize_stream(self, text: str,
                          callback: Callable[[bytes], None]):
        """
        合成并回调 WAV 字节（异步）
        """
        def _work():
            wav = self.synthesize(text)
            if wav:
                callback(wav)
        threading.Thread(target=_work, daemon=True).start()