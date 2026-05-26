"""
基于 Sherpa-ONNX 的流式语音识别（ASR）模块。

使用中英双语 Zipformer Transducer 模型，从麦克风实时采集音频并逐字输出识别文字。
首次运行时自动下载模型文件到 models/ 目录。
"""

import sys
import tarfile
import threading
import time
import urllib.request
from pathlib import Path

import sounddevice as sd
import sherpa_onnx

# ---------------------------------------------------------------------------
# 模型配置
# ---------------------------------------------------------------------------

# 预训练模型名称：中英双语流式 Zipformer Transducer
MODEL_NAME = "sherpa-onnx-streaming-zipformer-bilingual-zh-en-2023-02-20"

# 模型压缩包内包含的 4 个必要文件
MODEL_FILES = [
    f"{MODEL_NAME}/tokens.txt",                      # 词表文件，定义模型输出的 token 集合
    f"{MODEL_NAME}/encoder-epoch-99-avg-1.onnx",     # 编码器：将音频特征编码为高维表示
    f"{MODEL_NAME}/decoder-epoch-99-avg-1.onnx",     # 解码器：根据编码器输出预测文字 token
    f"{MODEL_NAME}/joiner-epoch-99-avg-1.onnx",      # 连接器：融合编码器和解码器的输出
]

# 模型下载地址（GitHub Releases）
MODEL_URL = (
    f"https://github.com/k2-fsa/sherpa-onnx/releases/download/"
    f"asr-models/{MODEL_NAME}.tar.bz2"
)

# 下载配置
MAX_RETRIES = 3       # 最大重试次数
RETRY_DELAY = 3        # 重试间隔（秒）


def _download_with_progress(url: str, dest: Path) -> None:
    """带进度条和重试机制的下载函数。

    使用 urllib 的 reporthook 回调显示下载进度百分比。
    下载失败时自动重试，最多重试 MAX_RETRIES 次。

    参数:
        url: 下载链接。
        dest: 保存路径。

    异常:
        OSError: 多次重试后仍然下载失败。
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            # 记录已下载字节数，用于进度计算
            downloaded = 0

            def _progress(block_count: int, block_size: int, total_size: int):
                """urllib reporthook 回调，每下载一个数据块触发一次。"""
                nonlocal downloaded
                downloaded = block_count * block_size
                if total_size > 0:
                    percent = min(int(downloaded / total_size * 100), 100)
                    bar = "█" * (percent // 2) + "░" * (50 - percent // 2)
                    sys.stdout.write(
                        f"\r  下载进度: |{bar}| {percent}% "
                        f"({downloaded / 1024 / 1024:.1f} / {total_size / 1024 / 1024:.1f} MB)"
                    )
                    sys.stdout.flush()

            urllib.request.urlretrieve(url, str(dest), reporthook=_progress)
            print()  # 下载完成后换行
            return  # 下载成功，退出

        except OSError as e:
            if attempt < MAX_RETRIES:
                wait = RETRY_DELAY * attempt
                print(f"\n  下载失败: {e}")
                print(f"  {wait} 秒后重试 (第 {attempt}/{MAX_RETRIES} 次)...")
                time.sleep(wait)
            else:
                print(f"\n  已重试 {MAX_RETRIES} 次，下载仍然失败。")
                raise


def _resolve_model_dir(model_dir: str | Path) -> Path:
    """解析模型目录，优先使用 PyInstaller 打包的内置模型。"""
    model_dir = Path(model_dir)
    if getattr(sys, "frozen", False):
        bundle_dir = Path(sys._MEIPASS)
        # 兼容 PyInstaller 6.x onedir 布局
        bundled = bundle_dir / "models"
        if not bundled.exists():
            bundled = bundle_dir / "_internal" / "models"
            
        if bundled.exists():
            return bundled
    return model_dir


def _download_model(model_dir: Path) -> None:
    """下载并解压 ASR 模型（如果本地未缓存）。

    检查 models/ 目录下是否已有完整的模型文件，如果没有则从 GitHub 下载
    压缩包并解压，解压完成后删除压缩包以节省磁盘空间。

    如果自动下载反复失败，可以手动下载模型：
      1. 浏览器打开: https://github.com/k2-fsa/sherpa-onnx/releases
      2. 搜索 {MODEL_NAME} 并下载 .tar.bz2 文件
      3. 解压到 models/ 目录，保持解压后的文件夹名不变
      4. 重新运行 python main.py

    参数:
        model_dir: 模型存放目录的 Path 对象。
    """
    # 如果所有模型文件都已存在，跳过下载
    if all((model_dir / f).exists() for f in MODEL_FILES):
        return

    # 确保模型目录存在
    model_dir.mkdir(parents=True, exist_ok=True)
    tar_path = model_dir / f"{MODEL_NAME}.tar.bz2"

    # 如果压缩包未下载，先从 GitHub Releases 下载
    if not tar_path.exists():
        # 显示文件大小信息
        print(f"正在下载模型 ({MODEL_NAME})")
        print(f"  地址: {MODEL_URL}")
        print(f"  文件大小: 约 100 MB，请耐心等待...")
        try:
            _download_with_progress(MODEL_URL, tar_path)
        except OSError as e:
            print(f"\n自动下载失败: {e}")
            print(f"请手动下载模型并解压到 {model_dir}/ 目录后重试。")
            print(f"手动下载地址: {MODEL_URL}")
            sys.exit(1)

    # 解压模型文件到 models/ 目录
    print("正在解压模型...")
    try:
        with tarfile.open(tar_path, "r:bz2") as tar:
            tar.extractall(path=model_dir, filter="data")
        print("模型准备就绪。\n")
    except Exception as e:
        print(f"\n解压模型失败: {e}")
        print("压缩包可能损坏，正在清理并建议重新运行程序。")
        # 清理损坏的文件和文件夹
        if tar_path.exists(): tar_path.unlink()
        import shutil
        model_subdir = model_dir / MODEL_NAME
        if model_subdir.exists(): shutil.rmtree(model_subdir)
        sys.exit(1)
    finally:
        # 无论成功还是在解压阶段抛出非解压相关的异常，
        # 只要代码执行到这，且 tar_path 还在，就删除它
        if tar_path.exists():
            tar_path.unlink()


class LiveASR:
    """流式语音识别器，封装 Sherpa-ONNX 的麦克风实时识别能力。

    使用 transducer 模型（编码器-解码器-连接器架构）进行流式解码，
    在独立线程中运行识别循环，通过回调函数输出识别结果。

    使用示例:
        asr = LiveASR(model_dir="models")
        asr.start(callback=lambda text: print(text))
        # ... 对着麦克风说话 ...
        asr.stop()
    """

    def __init__(
        self,
        model_dir: str = "models",
        sample_rate: int = 48000,
        provider: str = "cpu",
        num_threads: int = 1,
        decoding_method: str = "greedy_search",
        enable_endpoint_detection: bool = True,
    ):
        """初始化语音识别器。

        参数:
            model_dir: 模型文件存放目录，默认为 "models"。
            sample_rate: 麦克风采样率（Hz），默认 48000。
                         Sherpa-ONNX 内部会自动重采样到模型需要的 16000Hz。
            provider: ONNX Runtime 执行后端，可选 "cpu"、"cuda"、"coreml"。
            num_threads: ONNX Runtime 使用的线程数。
            decoding_method: 解码策略，可选 "greedy_search"（贪心搜索）
                             或 "modified_beam_search"（改进的束搜索）。
            enable_endpoint_detection: 是否启用端点检测（自动检测句子结束）。
        """
        # 音频采集参数
        self._sample_rate = sample_rate
        self._samples_per_read = int(0.1 * sample_rate)  # 每次读取 100 毫秒的音频数据

        # 运行时状态
        self._stream: sherpa_onnx.OnlineStream | None = None  # sherpa-onnx 识别流
        self._running = False                                   # 是否正在运行
        self._thread: threading.Thread | None = None            # 音频采集线程

        # 确保模型文件存在，不存在则自动下载
        model_dir = _resolve_model_dir(model_dir)
        _download_model(model_dir)

        # 创建 transducer 模型的在线识别器
        # transducer 模型 = encoder + decoder + joiner 三件套
        self._recognizer = sherpa_onnx.OnlineRecognizer.from_transducer(
            tokens=str(model_dir / MODEL_FILES[0]),       # 词表
            encoder=str(model_dir / MODEL_FILES[1]),      # 编码器
            decoder=str(model_dir / MODEL_FILES[2]),      # 解码器
            joiner=str(model_dir / MODEL_FILES[3]),       # 连接器
            num_threads=num_threads,                      # 推理线程数
            sample_rate=16000,                            # 模型内部采样率（固定 16kHz）
            feature_dim=80,                               # 声学特征维度
            decoding_method=decoding_method,              # 解码策略
            provider=provider,                            # 推理后端
            enable_endpoint_detection=enable_endpoint_detection,  # 端点检测
        )

    def start(self, callback) -> None:
        """启动流式语音识别。

        在后台守护线程中打开麦克风，持续采集音频数据并送入识别器。
        每当识别结果有更新时，调用 callback(text) 输出最新文字。
        支持端点检测（停顿换行）。

        参数:
            callback: 回调函数，签名为 callback(text: str)。
                      每次识别文字更新时被调用。如果 text 以 \n 结尾，表示句子结束。
        """
        self._running = True

        # 创建一个识别流，每个识别流代表一次独立的识别会话
        self._stream = self._recognizer.create_stream()

        def _run():
            """音频采集和识别的主循环，运行在后台守护线程中。"""
            last_result = ""  # 上一次的识别结果，用于去重

            # 打开默认麦克风的输入流
            # channels=1: 单声道
            # dtype="float32": 32 位浮点采样
            # samplerate: 麦克风采样率（sherpa-onnx 内部会自动重采样到 16kHz）
            with sd.InputStream(
                channels=1, dtype="float32", samplerate=self._sample_rate
            ) as s:
                while self._running:
                    # 阻塞读取 100ms 的音频数据
                    samples, _ = s.read(self._samples_per_read)
                    # 将多维数组展平为一维
                    samples = samples.reshape(-1)

                    # 将音频波形送入识别流
                    self._stream.accept_waveform(self._sample_rate, samples)

                    # 当模型有足够数据可供解码时，持续解码
                    while self._recognizer.is_ready(self._stream):
                        self._recognizer.decode_stream(self._stream)

                    # 获取当前已经识别出的文字
                    result = self._recognizer.get_result(self._stream).strip()

                    # 只有在新结果与上一次不同时才回调（避免重复输出）
                    if result and result != last_result:
                        last_result = result
                        callback(result)
                    
                    # 检测到端点（一句话结束/长停顿）
                    if self._recognizer.is_endpoint(self._stream):
                        if result:
                            # 发送一个带换行的最终结果，通知 UI 换行
                            callback(result + "\n")
                        # 重置流以清除缓冲区，开始下一句识别
                        self._recognizer.reset(self._stream)
                        last_result = ""

        # 创建守护线程：主线程退出时自动结束，避免阻塞程序退出
        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """停止流式语音识别。

        设置停止标志位，等待后台线程结束采集循环。
        """
        self._running = False
        if self._thread is not None:
            # 等待线程退出，避免资源泄漏
            self._thread.join()
