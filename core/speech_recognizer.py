"""
语音识别模块 —— Whisper (faster-whisper)
实时采集麦克风音频 → 转写为中文文本
"""
import queue
import threading
import numpy as np
from typing import Callable, Optional
from utils import logger, get_config


class SpeechRecognizer:
    """
    Whisper 实时语音识别封装
    - 默认 faster-whisper（CTranslate2 加速）
    - 支持 stream 回调
    """

    def __init__(self):
        cfg = get_config()["asr"]
        self.backend = cfg["backend"]
        self.model_size = cfg["model_size"]
        self.language = cfg["language"]
        self.device = cfg["device"]
        self.compute_type = cfg["compute_type"]

        self.model = None
        self.audio_queue: queue.Queue = queue.Queue()
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def load(self) -> bool:
        """加载 Whisper 模型"""
        logger.info(f"正在加载 ASR: faster-whisper {self.model_size}...")
        try:
            from faster_whisper import WhisperModel
            self.model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
            )
            logger.info(f"ASR 模型已加载: {self.model_size}")
            return True
        except Exception as e:
            logger.error(f"ASR 加载失败: {e}")
            return False

    # ------------------------------------------------------------
    # 实时录音 + 转写
    # ------------------------------------------------------------
    def start(self, callback: Callable[[str], None]):
        """启动后台录音线程"""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._record_loop, args=(callback,), daemon=True
        )
        self._thread.start()
        logger.info("语音识别已启动")

    def stop(self):
        """停止录音"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        logger.info("语音识别已停止")

    def _record_loop(self, callback: Callable[[str], None]):
        """录音 → VAD → 转写 循环"""
        try:
            import pyaudio
        except ImportError:
            logger.error("pyaudio 未安装")
            return

        chunk = 1024
        rate = 16000
        format = pyaudio.paInt16
        channels = 1

        p = pyaudio.PyAudio()
        stream = p.open(
            format=format, channels=channels,
            rate=rate, input=True,
            frames_per_buffer=chunk,
        )

        buffer = []
        silence_frames = 0
        speech_threshold = 500       # 音量阈值
        silence_limit = 40           # 连续静音帧数才切分

        logger.info("录音线程运行中...")

        while self._running:
            try:
                data = stream.read(chunk, exception_on_overflow=False)
                audio = np.frombuffer(data, dtype=np.int16)
                volume = np.abs(audio).mean()

                if volume > speech_threshold:
                    silence_frames = 0
                    buffer.append(audio)
                elif buffer:
                    silence_frames += 1
                    buffer.append(audio)
                    if silence_frames >= silence_limit:
                        self.audio_queue.put(np.concatenate(buffer))
                        buffer.clear()
                        silence_frames = 0
            except Exception as e:
                logger.error(f"录音异常: {e}")
                break

        stream.stop_stream()
        stream.close()
        p.terminate()

        # 处理队列中的转写任务
        self._transcribe_worker(callback)

    def _transcribe_worker(self, callback: Callable[[str], None]):
        """后台转写线程"""
        while self._running or not self.audio_queue.empty():
            try:
                audio = self.audio_queue.get(timeout=0.5)
                audio_f32 = audio.astype(np.float32) / 32768.0
                segments, _ = self.model.transcribe(
                    audio_f32, language=self.language, beam_size=5
                )
                for seg in segments:
                    text = seg.text.strip()
                    if text:
                        logger.info(f"ASR: {text}")
                        callback(text)
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"转写异常: {e}")

    def transcribe_file(self, audio_path: str) -> str:
        """转写音频文件（非实时）"""
        if not self.model:
            self.load()
        segments, _ = self.model.transcribe(audio_path, language=self.language)
        return " ".join(seg.text for seg in segments)