"""
基于 Faster-Whisper 的高精度语音识别模块。
提供目前最强的离线识别效果，支持自动标点和中英混读。
"""

import sys
import threading
import time
import traceback
import queue
import os
from pathlib import Path
from live_agent.utils.logger import get_logger

import sounddevice as sd
from faster_whisper import WhisperModel
import numpy as np

logger = get_logger("ASR")

# ---------------------------------------------------------------------------
# 模型配置
# ---------------------------------------------------------------------------
MODEL_SIZE = "base"

def _resolve_model_dir(base_dir: str | Path) -> str:
    """解析模型存储目录，支持 PyInstaller 打包环境。"""
    if getattr(sys, "frozen", False):
        bundle_dir = Path(sys._MEIPASS)
        # 探测顺序：1. _internal/models/whisper (PyInstaller 6+) 2. models/whisper
        for p in [bundle_dir / "_internal" / "models" / "whisper", bundle_dir / "models" / "whisper"]:
            if p.exists():
                logger.info(f"找到打包内置模型: {p}")
                return str(p.absolute())

    # 开发环境下
    path = Path(base_dir) / "whisper"
    path.mkdir(parents=True, exist_ok=True)
    return str(path.absolute())


class LiveASR:
    def __init__(
        self,
        model_dir: str = "models",
        **kwargs
    ):
        self._model_dir = _resolve_model_dir(model_dir)
        self._model = None
        self._running = False
        self._audio_queue = queue.Queue()
        self._worker_thread = None
        logger.info(f"准备 ASR 引擎 (模型级别: {MODEL_SIZE})")

    def start(self, callback, state_callback=None, device=None) -> None:
        """
        启动识别。
        callback: 接收识别文字。
        state_callback: 接收状态变化 (str: "initializing", "running", "failed")。
        """
        if self._running: return
        self._running = True
        
        def _notify_state(state):
            if state_callback:
                state_callback(state)

        def _worker():
            try:
                _notify_state("initializing")
                
                # 1. 确定采样率 (强制 ASR 引擎使用 16000Hz 核心)
                TARGET_RATE = 16000
                try:
                    # 如果 device 为 None 或 -1，使用默认设备
                    if device is None or device < 0:
                        device_info = sd.query_devices(kind='input')
                        input_rate = int(device_info['default_samplerate'])
                        actual_device = None # sd.InputStream 传 None 会用默认
                    else:
                        device_info = sd.query_devices(device, 'input')
                        input_rate = int(device_info['default_samplerate'])
                        actual_device = device
                except Exception as e:
                    logger.warning(f"无法获取设备 {device} 信息: {e}, 尝试默认设置")
                    input_rate = 16000
                    actual_device = None
                
                logger.info(f"ASR 引擎启动... 输入: {input_rate}Hz -> 识别: {TARGET_RATE}Hz")

                # 2. 初始化引擎
                if not self._model:
                    logger.info(f"正在加载模型: {self._model_dir}")
                    self._model = WhisperModel(
                        MODEL_SIZE, 
                        device="cpu", 
                        compute_type="int8",
                        download_root=self._model_dir
                    )
                logger.info("ASR 模型加载/就绪成功")

                def _audio_callback(indata, frames, time_info, status):
                    if status: logger.warning(f"硬件提示: {status}")
                    if not self._running: raise sd.CallbackStop
                    self._audio_queue.put(indata.flatten().copy())

                # 3. 开启录音
                with sd.InputStream(
                    channels=1, dtype="float32", samplerate=input_rate,
                    device=actual_device, callback=_audio_callback
                ):
                    logger.info("麦克风监听流已开启")
                    _notify_state("running")
                    
                    audio_buffer = np.array([], dtype=np.float32)
                    SILENCE_THRESHOLD = 0.01
                    MAX_BUFFER_LEN = TARGET_RATE * 5
                    MIN_BUFFER_LEN = TARGET_RATE * 0.8
                    last_voice_time = time.time()

                    while self._running:
                        try:
                            try:
                                chunk = self._audio_queue.get(timeout=0.2)
                            except queue.Empty: continue

                            # 降采样
                            if input_rate == 32000:
                                chunk_16k = chunk[::2]
                            elif input_rate == 48000:
                                chunk_16k = chunk[::3]
                            else:
                                chunk_16k = chunk
                            
                            audio_buffer = np.append(audio_buffer, chunk_16k)
                            energy = np.sqrt(np.mean(chunk_16k**2))
                            if energy > SILENCE_THRESHOLD:
                                last_voice_time = time.time()
                            
                            now = time.time()
                            if len(audio_buffer) > MIN_BUFFER_LEN:
                                if (now - last_voice_time > 0.6) or (len(audio_buffer) > MAX_BUFFER_LEN):
                                    # 执行识别
                                    segments, info = self._model.transcribe(
                                        audio_buffer, 
                                        beam_size=5,
                                        language="zh",
                                        initial_prompt="这是一段简体中文的直播对话内容。", # 引导模型输出简体
                                        vad_filter=True,
                                        vad_parameters=dict(min_silence_duration_ms=500)
                                    )

                                    full_text = "".join([s.text for s in segments])
                                    if full_text.strip():
                                        logger.info(f"[Whisper Result] {full_text}")
                                        callback(full_text + "\n")
                                    audio_buffer = np.array([], dtype=np.float32)

                        except Exception as e:
                            logger.error(f"识别循环异常: {e}")

            except Exception as e:
                logger.error(f"ASR 工作线程崩溃: {e}\n{traceback.format_exc()}")
                _notify_state("failed")
            finally:
                self._running = False
                logger.info("ASR 识别线程已退出")

        self._worker_thread = threading.Thread(target=_worker, daemon=True)
        self._worker_thread.start()

    def stop(self) -> None:
        self._running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=1.0)
