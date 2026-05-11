"""
全管线编排器 —— 把所有引擎串联起来
摄像头 → 人脸检测 → 情绪识别 → 对话 → TTS → 数字人渲染 + 唇形同步
"""
import time
import threading
import queue
import numpy as np
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass, field
from enum import Enum, auto

from utils import logger, get_config
from core.camera_capture import CameraCapture
from core.face_detector import FaceDetector, FaceData
from core.emotion_recognizer import EmotionRecognizer, Emotion
from core.llm_engine import LLMEngine
from core.speech_recognizer import SpeechRecognizer
from core.speech_synthesizer import SpeechSynthesizer
from core.avatar_renderer import AvatarRenderer
from core.lip_sync import LipSync
from core.speech_synthesizer import SpeechSynthesizer, HAS_SOUND


class PipelineState(Enum):
    IDLE = auto()
    LISTENING = auto()       # 等待用户说话
    THINKING = auto()        # LLM 推理中
    SPEAKING = auto()        # TTS 播放中
    ERROR = auto()


@dataclass
class PipelineFrame:
    """管线一帧的完整数据"""
    timestamp: float = 0.0
    emotion: Emotion = Emotion.NEUTRAL
    emotion_conf: float = 0.0
    mouth_openness: float = 0.0
    face_detected: bool = False
    face_data: Optional[FaceData] = None
    state: PipelineState = PipelineState.IDLE


class Pipeline:
    """
    情感陪伴管线编排器
    管理所有模块的生命周期和数据流
    """

    def __init__(self):
        self.cfg = get_config()

        # ---- 引擎 ----
        self.camera: Optional[CameraCapture] = None
        self.face_detector: Optional[FaceDetector] = None
        self.emotion_recognizer: Optional[EmotionRecognizer] = None
        self.llm_engine: Optional[LLMEngine] = None
        self.speech_recognizer: Optional[SpeechRecognizer] = None
        self.speech_synthesizer: Optional[SpeechSynthesizer] = None
        self.avatar_renderer: Optional[AvatarRenderer] = None
        self.lip_sync: Optional[LipSync] = None

        # ---- 状态 ----
        self.state: PipelineState = PipelineState.IDLE
        self.current_emotion: Emotion = Emotion.NEUTRAL
        self.chat_history: list = []                 # [(role, text)]
        self.latest_frame: PipelineFrame = PipelineFrame()

        # ---- 回调 ----
        self.on_emotion_change: Optional[Callable[[Emotion, float], None]] = None
        self.on_state_change: Optional[Callable[[PipelineState], None]] = None
        self.on_asr_result: Optional[Callable[[str], None]] = None
        self.on_llm_response: Optional[Callable[[str], None]] = None
        self.on_lipsync_update: Optional[Callable[[float], None]] = None

        # ---- 线程 ----
        self._running: bool = False
        self._pipeline_thread: Optional[threading.Thread] = None
        self._message_queue: queue.Queue = queue.Queue()

        # ---- 性能 ----
        self._frame_count: int = 0
        self._fps_timer: float = time.time()
        self.current_fps: float = 0.0

    # ============================================================
    # 初始化 (渐进式加载)
    # ============================================================
    def init_basic(self) -> bool:
        """初始化基础模块（摄像头 + 人脸 + 情绪 + 数字人）"""
        try:
            self.face_detector = FaceDetector()
            self.emotion_recognizer = EmotionRecognizer()
            self.avatar_renderer = AvatarRenderer()
            self.lip_sync = LipSync()

            logger.info("✅ 基础管线已初始化")
            return True
        except Exception as e:
            logger.error(f"基础管线初始化失败: {e}")
            return False

    def init_camera(self, camera_id: int = 0) -> bool:
        """初始化摄像头"""
        self.camera = CameraCapture()
        if not self.camera.open(camera_id):
            return False
        return True

    def init_llm(self) -> bool:
        """加载 LLM（较重，按需）"""
        self.llm_engine = LLMEngine()
        return self.llm_engine.load()

    def init_asr(self) -> bool:
        """加载语音识别"""
        self.speech_recognizer = SpeechRecognizer()
        return self.speech_recognizer.load()

    def init_tts(self) -> bool:
        """加载语音合成"""
        self.speech_synthesizer = SpeechSynthesizer()
        return self.speech_synthesizer.load()

    # ============================================================
    # 运行控制
    # ============================================================
    def start(self):
        """启动管线主循环"""
        if self._running:
            return
        self._running = True

        if self.camera and not self.camera.is_running:
            self.camera.start()

        self._pipeline_thread = threading.Thread(
            target=self._pipeline_loop, daemon=True
        )
        self._pipeline_thread.start()
        self._set_state(PipelineState.IDLE)
        logger.info("🚀 管线主循环已启动")

    def stop(self):
        """停止管线"""
        self._running = False
        if self.camera:
            self.camera.stop()
        if self._pipeline_thread:
            self._pipeline_thread.join(timeout=3)
        self._set_state(PipelineState.IDLE)
        logger.info("⏸ 管线已停止")

    # ============================================================
    # 主循环
    # ============================================================
    def _pipeline_loop(self):
        """管线主循环（后台线程）"""
        cycle_time = 1.0 / 30.0       # ~30FPS
        last_time = time.time()

        while self._running:
            dt = time.time() - last_time
            last_time = time.time()

            # ---- Step 1: 摄像头帧 ----
            frame = None
            if self.camera:
                frame = self.camera.get_frame()

            face_data = None
            emotion = Emotion.NEUTRAL
            emotion_conf = 0.0

            if frame is not None and self.face_detector:
                # ---- Step 2: 人脸检测 ----
                face_data = self.face_detector.detect(frame)

                if face_data and self.emotion_recognizer:
                    # ---- Step 3: 情绪识别 ----
                    emotion, emotion_conf = self.emotion_recognizer.predict(
                        face_data.landmarks_478
                    )

                    if emotion != self.current_emotion:
                        self.current_emotion = emotion
                        if self.on_emotion_change:
                            self.on_emotion_change(emotion, emotion_conf)

                    # ---- Step 3.5: 头部姿态 → 数字人 ----
                    if self.avatar_renderer:
                        head_pose = self._estimate_head_pose(face_data.landmarks_478)
                        self.avatar_renderer.update_head_pose(*head_pose)
                        self.avatar_renderer.update_emotion(emotion, emotion_conf)

            # ---- Step 4: 更新数字人 ----
            if self.avatar_renderer:
                self.avatar_renderer.tick(dt)

            # ---- Step 5: 处理消息队列 ----
            self._process_messages()

            # ---- Step 6: 保存帧状态 ----
            self.latest_frame = PipelineFrame(
                timestamp=time.time(),
                emotion=emotion,
                emotion_conf=emotion_conf,
                face_detected=face_data is not None,
                face_data=face_data,
                state=self.state,
            )

            # ---- FPS 统计 ----
            self._frame_count += 1
            if self._frame_count % 30 == 0:
                now = time.time()
                self.current_fps = 30.0 / max(now - self._fps_timer, 0.001)
                self._fps_timer = now

            # ---- 帧率控制 ----
            elapsed = time.time() - last_time
            sleep_time = max(0, cycle_time - elapsed)
            if sleep_time > 0.001:
                time.sleep(sleep_time)

    # ============================================================
    # 消息处理
    # ============================================================
    def send_message(self, text: str):
        """用户发送消息"""
        self._message_queue.put(("user_text", text))

    def send_voice(self, audio_data: bytes):
        """用户语音输入（预留）"""
        self._message_queue.put(("user_voice", audio_data))

    def _process_messages(self):
        """处理消息队列"""
        try:
            while True:
                msg_type, payload = self._message_queue.get_nowait()
                if msg_type == "user_text":
                    self._handle_user_text(payload)
        except queue.Empty:
            pass

    def _handle_user_text(self, text: str):
        """处理用户文字输入"""
        logger.info(f"📩 用户: {text}")
        self.chat_history.append(("user", text))
        self._set_state(PipelineState.THINKING)

        # LLM 推理
        if not self.llm_engine:
            logger.warning("LLM 未加载")
            self._set_state(PipelineState.IDLE)
            return

        history_str = "\n".join(
            f"{'用户' if r == 'user' else 'AI'}: {t}"
            for r, t in self.chat_history[-10:]
        )

        try:
            response = self.llm_engine.chat(
                user_input=text,
                emotion=self.current_emotion.cn_name,
                history=history_str,
            )
            self.chat_history.append(("ai", response))

            if self.on_llm_response:
                self.on_llm_response(response)

            # TTS 合成
            if self.speech_synthesizer:
                self._set_state(PipelineState.SPEAKING)
                self._speak_and_sync(response)

        except Exception as e:
            logger.error(f"LLM 错误: {e}")
            self._set_state(PipelineState.ERROR)

        self._set_state(PipelineState.IDLE)

    def _speak_and_sync(self, text: str):
        """合成语音 + 驱动唇形"""
        if not HAS_SOUND:
            return

        try:
            import soundfile as sf

            wav_bytes = self.speech_synthesizer.synthesize(text)
            if wav_bytes is None:
                return

            audio, sr = sf.read(io.BytesIO(wav_bytes))
            if audio.ndim > 1:
                audio = audio.mean(axis=1)

            # 逐帧分析唇形
            chunk_size = int(0.04 * sr)
            hop_size = int(0.02 * sr)

            for i in range(0, len(audio) - chunk_size, hop_size):
                chunk = audio[i:i + chunk_size]
                openness = self.lip_sync.process_audio_chunk(chunk, sr)
                if self.on_lipsync_update:
                    self.on_lipsync_update(openness)
                if self.avatar_renderer:
                    self.avatar_renderer.update_mouth(openness)
                time.sleep(0.02)

            # TTS 播放（非阻塞）
            self.speech_synthesizer.speak(text, blocking=False)

        except Exception as e:
            logger.error(f"语音合成/唇形同步失败: {e}")

    # ============================================================
    # 头部姿态估算
    # ============================================================
    def _estimate_head_pose(self, landmarks: np.ndarray) -> tuple:
        """
        从 478 关键点估算头部姿态
        返回 (tilt_x, tilt_y) — 归一化俯仰/偏转
        """
        # 鼻尖
        nose = landmarks[1, :2]
        # 左右眼内角
        left_eye = landmarks[133, :2]
        right_eye = landmarks[362, :2]
        # 嘴角
        left_mouth = landmarks[61, :2]
        right_mouth = landmarks[291, :2]

        # 眼距用于归一化
        eye_dist = np.linalg.norm(left_eye - right_eye) + 1e-6

        # 水平偏转：鼻子相对两眼中心的偏移
        eye_center = (left_eye + right_eye) / 2
        tilt_y = (nose[0] - eye_center[0]) / eye_dist * 2.0

        # 俯仰：鼻子到眼中心 vs 鼻子到嘴中心的垂直比
        mouth_center = (left_mouth + right_mouth) / 2
        nose_to_eye = eye_center[1] - nose[1]
        nose_to_mouth = mouth_center[1] - nose[1]
        tilt_x = (nose_to_mouth / max(nose_to_eye, 0.01) - 1.0) * 0.5

        return (np.clip(tilt_x, -1, 1), np.clip(tilt_y, -1, 1))

    # ============================================================
    # 状态管理
    # ============================================================
    def _set_state(self, state: PipelineState):
        if state != self.state:
            self.state = state
            if self.on_state_change:
                self.on_state_change(state)

    # ============================================================
    # 清理
    # ============================================================
    def shutdown(self):
        """完整关闭"""
        self.stop()
        if self.camera:
            self.camera.close()
        if self.face_detector:
            self.face_detector.release()
        if self.llm_engine:
            self.llm_engine.unload()
        logger.info("🧹 管线已完全关闭")