"""
大语言模型引擎 —— Qwen2 7B 对话
支持: Transformers (4‑bit 量化) / llama.cpp (GGUF)
"""
import os
import threading
from typing import Generator, Callable, Optional
from utils import logger, get_config
from utils.platform_utils import get_data_dir, get_num_threads


class LLMEngine:
    """
    对话引擎封装
    - 默认 transformers 后端
    - 可通过 backend 切换为 llama.cpp
    - 流式输出 (token callback)
    """

    def __init__(self):
        cfg = get_config()["llm"]
        self.backend = cfg["backend"]
        self.model_id = cfg["model_id"]
        self.quantize = cfg["quantize"]
        self.max_tokens = cfg["max_tokens"]
        self.temperature = cfg["temperature"]
        self.top_p = cfg["top_p"]
        self.system_prompt = cfg["system_prompt"]

        self.model = None
        self.tokenizer = None
        self._lock = threading.Lock()
        self._loaded = False

    # ------------------------------------------------------------
    # 模型加载
    # ------------------------------------------------------------
    def load(self) -> bool:
        """加载模型（阻塞）"""
        if self._loaded:
            return True

        logger.info(f"正在加载 LLM: {self.model_id} (backend={self.backend}, quant={self.quantize})...")

        if self.backend == "transformers":
            return self._load_transformers()
        elif self.backend == "llama.cpp":
            return self._load_llama_cpp()
        else:
            logger.error(f"不支持的 LLM backend: {self.backend}")
            return False

    def _load_transformers(self) -> bool:
        try:
            from transformers import (
                AutoModelForCausalLM,
                AutoTokenizer,
                BitsAndBytesConfig,
            )
            import torch

            if self.quantize == "4bit":
                bnb_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_use_double_quant=True,
                )
            else:
                bnb_config = None

            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_id, trust_remote_code=True
            )
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_id,
                quantization_config=bnb_config,
                device_map="auto",
                trust_remote_code=True,
            )
            self._loaded = True
            logger.info(f"LLM 已加载: {self.model_id} (device={self.model.device})")
            return True

        except Exception as e:
            logger.error(f"Transformers 加载失败: {e}")
            return False

    def _load_llama_cpp(self) -> bool:
        """加载 GGUF 量化模型"""
        try:
            from llama_cpp import Llama
            model_path = self.cfg.get("gguf_model", "models/qwen2-1_5b-instruct-q4_k_m.gguf")
            # 绝对路径
            if not os.path.isabs(model_path):
                model_path = os.path.join(get_data_dir(), model_path)
            if not os.path.exists(model_path):
                logger.error(f"GGUF 模型未找到: {model_path}")
                return False
            self.model = Llama(
                model_path=model_path,
                n_ctx=2048,
                n_threads=get_num_threads(),
                verbose=False,
            )
            self._loaded = True
            logger.info(f"llama.cpp 模型已加载: {model_path}")
            return True
        except Exception as e:
            logger.error(f"llama.cpp 加载失败: {e}")
            return False

    # ------------------------------------------------------------
    # 对话接口
    # ------------------------------------------------------------
    def chat(
        self,
        user_input: str,
        emotion: str = "neutral",
        history: str = "",
        callback: Optional[Callable[[str], None]] = None,
    ) -> str:
        """
        发送消息 → 返回完整回复
        callback 用于流式逐 token 返回
        """
        with self._lock:
            prompt = self._build_prompt(user_input, emotion, history)
            return self._generate(prompt, callback)

    def _build_prompt(self, user_input: str, emotion: str, history: str) -> str:
        """构建 Qwen2 Chat 格式提示词"""
        system = self.system_prompt.format(
            emotion=emotion, history=history, input=user_input
        )

        # Qwen2 ChatML 格式
        if self.backend == "transformers" and self.tokenizer:
            messages = [
                {"role": "system", "content": system},
            ]
            if history:
                messages.append({"role": "user", "content": history})
            messages.append({"role": "user", "content": user_input})

            return self.tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
        else:
            return f"<|im_start|>system\n{system}<|im_end|>\n<|im_start|>user\n{user_input}<|im_end|>\n<|im_start|>assistant\n"

    def _generate(
        self, prompt: str, callback: Optional[Callable[[str], None]]
    ) -> str:
        """执行推理"""
        if self.backend == "transformers":
            return self._generate_transformers(prompt, callback)
        elif self.backend == "llama.cpp":
            return self._generate_llama_cpp(prompt, callback)
        else:
            return "⚠ LLM 未加载"

    def _generate_transformers(
        self, prompt: str, callback: Optional[Callable[[str], None]]
    ) -> str:
        import torch

        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=self.max_tokens,
                temperature=self.temperature,
                top_p=self.top_p,
                do_sample=True,
            )
        response = self.tokenizer.decode(
            outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True
        )
        if callback:
            callback(response)
        return response.strip()

    def _generate_llama_cpp(
        self, prompt: str, callback: Optional[Callable[[str], None]]
    ) -> str:
        tokens = []
        for chunk in self.model(prompt, max_tokens=self.max_tokens, stream=True):
            text = chunk["choices"][0].get("text", "")
            tokens.append(text)
            if callback:
                callback(text)
        return "".join(tokens).strip()

    def unload(self):
        """释放模型显存"""
        if self.model:
            del self.model
            self.model = None
            self._loaded = False
            import gc
            gc.collect()
            logger.info("LLM 已卸载")