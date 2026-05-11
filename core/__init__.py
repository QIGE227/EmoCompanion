"""
EmoCompanion 核心模块
"""
from core.face_detector import FaceDetector, FaceData
from core.emotion_recognizer import EmotionRecognizer, Emotion
from core.llm_engine import LLMEngine
from core.speech_recognizer import SpeechRecognizer
from core.speech_synthesizer import SpeechSynthesizer
from core.avatar_renderer import AvatarRenderer, AvatarState
from core.lip_sync import LipSync
from core.camera_capture import CameraCapture
from core.pipeline import Pipeline, PipelineState, PipelineFrame
