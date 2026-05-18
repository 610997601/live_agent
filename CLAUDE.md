# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Streaming real-time speech recognition (ASR) using Sherpa-ONNX with Python.
Supports Chinese-English bilingual recognition from microphone input, with keyword-triggered TTS voice replies via Microsoft Edge TTS.

## Commands

```bash
# Install dependencies
pip install -e .

# Run streaming ASR from microphone (auto-downloads model on first run)
python main.py
```

## Architecture

```
live_agent/
├── main.py               # Entry point: wires ASR → KeywordMatcher → TTS
├── live_agent/
│   ├── __init__.py        # Re-exports LiveASR, KeywordMatcher, EdgeTTS
│   ├── asr.py             # LiveASR: streaming speech recognition (Sherpa-ONNX)
│   ├── keyword.py         # KeywordMatcher: keyword detection in streaming text
│   └── tts.py             # EdgeTTS: text-to-speech via Microsoft Edge
├── models/                # Downloaded ONNX model files (gitignored)
└── pyproject.toml
```

### Data Flow

```
Microphone → LiveASR (Sherpa-ONNX transducer) → streaming text
    │
    ├─ print to terminal (real-time character-by-character)
    └─ KeywordMatcher.check(text) → on hit → EdgeTTS.speak(reply)
```

### Key Modules

- **LiveASR** (`asr.py`) — Sherpa-ONNX OnlineRecognizer with transducer model (bilingual zh-en). Auto-downloads model, opens microphone via sounddevice, runs recognition in daemon thread.

- **KeywordMatcher** (`keyword.py`) — Detects preset keywords in incremental ASR text. Deduplicates per conversation round (resets when text clears). Returns `KeywordHit(keyword, reply)` on match.

- **EdgeTTS** (`tts.py`) — Synthesizes text to MP3 via Microsoft Edge TTS, plays via system audio player (afplay/paplay/PowerShell). Runs in background thread, non-blocking.

### Dependencies

- `sherpa-onnx` — Streaming ASR (ONNX Runtime)
- `sounddevice` — Microphone audio capture
- `edge-tts` — Microsoft Edge text-to-speech
