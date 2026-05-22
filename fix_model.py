"""
ASR 模型修复与安装脚本 (增强版)。
执行该脚本将：
1. 清理损坏的模型残留。
2. 尝试从多个来源（GitHub / HuggingFace 镜像）下载模型。
3. 自动解压并验证完整性。
"""

import os
import sys
import tarfile
import urllib.request
import shutil
import time
from pathlib import Path

# 配置信息
MODEL_NAME = "sherpa-onnx-streaming-zipformer-bilingual-zh-en-2023-02-20"
# 来源 1: GitHub (原始地址)
URL_GITHUB = f"https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/{MODEL_NAME}.tar.bz2"
# 来源 2: HuggingFace (稳定镜像)
URL_HF = f"https://huggingface.co/csukuangfj/sherpa-onnx-streaming-zipformer-bilingual-zh-en-2023-02-20/resolve/main/{MODEL_NAME}.tar.bz2"

MODELS_DIR = Path("models")
TAR_PATH = MODELS_DIR / f"{MODEL_NAME}.tar.bz2"
EXTRACT_DIR = MODELS_DIR / MODEL_NAME

def progress_bar(block_count, block_size, total_size):
    """显示下载进度。"""
    downloaded = block_count * block_size
    if total_size > 0:
        percent = min(int(downloaded / total_size * 100), 100)
        bar = "█" * (percent // 2) + "░" * (50 - percent // 2)
        sys.stdout.write(f"\r    进度: |{bar}| {percent}% ({downloaded / 1024 / 1024:.1f} / {total_size / 1024 / 1024:.1f} MB)")
        sys.stdout.flush()

def download_file(url, label):
    print(f"\n[*] 尝试从 {label} 下载模型...")
    print(f"    地址: {url}")
    try:
        # 设置 User-Agent 模拟浏览器，避免被拦截
        opener = urllib.request.build_opener()
        opener.addheaders = [('User-agent', 'Mozilla/5.0')]
        urllib.request.install_opener(opener)
        
        urllib.request.urlretrieve(url, str(TAR_PATH), reporthook=progress_bar)
        print("\n    - 下载完成！")
        return True
    except Exception as e:
        print(f"\n    [!] {label} 下载失败: {e}")
        return False

def main():
    print("=== 直播助手 ASR 模型修复工具 (增强版) ===\n")

    # 1. 清理损坏文件
    print(f"[*] 步骤 1: 清理残留文件...")
    if MODELS_DIR.exists():
        if TAR_PATH.exists():
            TAR_PATH.unlink()
            print(f"  - 已清理临时压缩包")
        if EXTRACT_DIR.exists():
            shutil.rmtree(EXTRACT_DIR)
            print(f"  - 已清理旧模型文件夹")
    else:
        MODELS_DIR.mkdir(parents=True)
    
    # 2. 重新下载 (多源策略)
    success = False
    # 先尝试 HuggingFace (通常更快更稳)
    if download_file(URL_HF, "HuggingFace 镜像"):
        success = True
    # 如果失败，尝试 GitHub
    elif download_file(URL_GITHUB, "GitHub 原始地址"):
        success = True

    if not success:
        print("\n\n[!!!] 所有下载来源均已失败。")
        print("这通常是由于您的网络环境无法访问 GitHub 或 HuggingFace 导致的。")
        print("-" * 50)
        print("【手动解决办法】:")
        print(f"1. 请在浏览器中打开并下载: {URL_HF}")
        print(f"2. 将下载好的文件重命名为: {TAR_PATH.name}")
        print(f"3. 放入项目下的 models/ 目录中")
        print("4. 再次运行此脚本，它将自动为您解压验证。")
        print("-" * 50)
        return

    # 3. 解压
    print(f"\n[*] 步骤 3: 正在解压模型...")
    try:
        # 尝试检测文件是否真的是压缩包
        if not tarfile.is_tarfile(str(TAR_PATH)):
            raise Exception("下载的文件不是有效的 tar 压缩包 (可能下载到了错误页面)")
            
        with tarfile.open(TAR_PATH, "r:bz2") as tar:
            tar.extractall(path=MODELS_DIR)
        print("  - 解压完成！")
    except Exception as e:
        print(f"  [!] 解压失败: {e}")
        print("  提示：请确保下载的文件完整。如果反复失败，请尝试手动下载。")
        return
    finally:
        if TAR_PATH.exists():
            TAR_PATH.unlink()

    # 4. 验证
    print(f"\n[*] 步骤 4: 正在验证完整性...")
    required_files = [
        "tokens.txt",
        "encoder-epoch-99-avg-1.onnx",
        "decoder-epoch-99-avg-1.onnx",
        "joiner-epoch-99-avg-1.onnx"
    ]
    missing = []
    for f in required_files:
        if not (EXTRACT_DIR / f).exists():
            missing.append(f)
    
    if not missing:
        print("  [OK] 模型已成功安装并验证通过！")
        print("\n您现在可以重新运行程序了: python run_gui.py")
    else:
        print(f"  [!] 验证失败，缺失核心文件: {missing}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[!] 操作已由用户取消。")
