# 🎙️ 直播助手 (Live Assistant)

一款专为带货主播和直播运营设计的全功能桌面客户端。集成了**实时语音识别**、**智能关键词回复**、**百应平台同步**以及**定时循环弹幕**等核心功能，助您轻松掌控直播间互动。

![UI风格](https://img.shields.io/badge/风格-Apple--Inspired-blue)
![Python版本](https://img.shields.io/badge/Python-3.11%2B-green)
![平台支持](https://img.shields.io/badge/平台-Windows-blue)

---

## ✨ 核心功能

### 1. 🎤 语音识别 (ASR) & 自动语音回复
*   **实时转写**：基于 `Sherpa-ONNX` 的流式语音识别，超低延迟将主播语音转为文字。
*   **智能断句**：自动检测停顿并换行，聊天式展示识别记录。
*   **关键词命中**：实时监测主播话语，命中预设关键词后自动通过 `Edge-TTS` 播放高音质回复音频。

### 2. 🤖 百应回复配置同步
*   **智能回复切换**：一键开启/关闭百应平台的官方智能回复功能。
*   **云端规则管理**：在客户端内全量编辑百应关键词回复规则，支持 Excel 批量导入导出，一键同步到云端。
*   **嵌套编辑模式**：安全的弹窗管理机制，确保在后台数据刷新时编辑过程不受干扰。

### 3. 💬 定时循环弹幕 (本地持久化)
*   **自动化互动**：预设多条弹幕内容及发送间隔，系统自动在直播间循环发送。
*   **多任务并行**：支持同时开启多条定时规则，营造直播间热度。
*   **账号隔离**：根据登录账号自动保存对应的本地弹幕配置。

### 4. 🚀 授权登录与监控
*   **内置浏览器**：基于 `Playwright` 的内置浏览器，扫码即可授权，安全可靠。
*   **实时状态**：Header 区域实时显示账号头像、昵称及直播间在线状态（🟢 直播中 / ⚪️ 未开播）。

---

## 🛠️ 技术栈

*   **GUI 框架**：PySide6 (Qt for Python)
*   **语音识别**：Sherpa-ONNX (Zipformer 模型)
*   **语音合成**：Edge-TTS
*   **自动化控制**：Playwright
*   **包管理器**：UV (推荐)
*   **打包工具**：PyInstaller + NSIS

---

## 🚀 快速开始

### 1. 环境准备
确保您的电脑已安装 Python 3.11 或更高版本。推荐使用 [uv](https://github.com/astral-sh/uv) 进行依赖管理。

### 2. 安装依赖
```bash
# 同步环境
uv sync

# 安装 Playwright 浏览器内核
uv run playwright install chromium
```

### 3. 模型修复/下载
语音识别需要约 130MB 的模型文件。如果初次运行失败，请执行修复脚本：
```bash
python fix_model.py
```

### 4. 运行程序
```bash
python run_gui.py
```

---

## 📦 打包发布 (Windows)

如果您需要将程序打包成 `.exe` 分发给他人使用：

### 1. 快速打包
直接在根目录执行脚本：
```batch
build_windows.bat
```
打包产物位于 `dist/直播助手/` 目录下。

### 2. 制作安装包 (可选)
如果您安装了 [NSIS](https://nsis.sourceforge.io/)，可以右键点击 `直播助手.nsi` 并选择 "Compile NSIS Script" 来生成安装程序。

---

## 📂 数据存储

程序生成的配置文件、浏览器缓存及音频文件均按照操作系统规范存储在以下路径：

*   **Windows**: `%APPDATA%\BuyinAssistant`
    *   (通常路径：`C:\Users\您的用户名\AppData\Roaming\BuyinAssistant`)
*   **macOS**: `~/Library/Application Support/BuyinAssistant`
*   **Linux**: `~/.config/BuyinAssistant`

### 存储内容说明：
*   `rules.json`: 语音识别关键词规则。
*   `browser_session/`: 内置浏览器的登录状态与缓存。
*   `audio/`: 预生成的语音回复音频文件。
*   `{outer_id}/danmu_rules.json`: 按账号隔离的定时弹幕配置。

---

## 📂 项目结构

*   `live_agent/`：核心业务逻辑与 GUI 面板代码。
*   `models/`：存放 ASR 语音模型文件。
*   `fix_model.py`：模型下载与完整性校验工具。
*   `build.spec`：PyInstaller 打包配置文件。
*   `接口抓包整理.md`：百应平台 API 参考文档。

---

## ⚠️ 注意事项

1.  **浏览器环境**：运行“回复配置”或“定时弹幕”时，程序会启动一个内置浏览器窗口。请**务必保持该窗口开启**（可以最小化），关闭浏览器会导致同步断开。
2.  **麦克风权限**：语音识别功能需要系统麦克风权限，请确保在运行前已正确配置。
3.  **打包调试**：如果打包后的 `.exe` 无法启动，请将 `build.spec` 中的 `console=False` 改为 `True` 重新打包以查看详细日志。

---

## 📄 开源协议

本项目仅供学习与技术研究使用，请勿用于任何违反平台规则或法律法规的活动。
