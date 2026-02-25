# Architecture

## Overview

Chatterbox is a single-process voice agent with a modular pipeline architecture. Each component is isolated behind a simple interface and wired together by the pipeline orchestrator.

## State Machine

```
LISTENING ──(VAD speech end)──→ THINKING ──(first audio)──→ SPEAKING
    ↑                                                          │
    └────────────────────────── LISTENING ←──(playback done)───┘
```

After 60s of silence, conversation context is cleared but the app stays in LISTENING.

| State | Activity |
|-------|----------|
| LISTENING | Mic feeds frames to VAD, accumulates audio buffer |
| THINKING | Background thread: transcribe → LLM → TTS |
| SPEAKING | Background thread: play audio through speaker |

## Data Flow

```
Microphone (16kHz mono int16)
      │
      ▼
  MicStream.queue (30ms frames)
      │
      └──→ [LISTENING] VoiceActivityDetector
                └─ speech ends → buffer → Transcriber
                                              │
                                              ▼
                                    CharacterEngine (Ollama, streaming)
                                              │
                                              ▼
                                    Synthesizer (piper, sentence-buffered)
                                              │
                                              ▼
                                    Speaker → audio output
```

## Threading Model

- **Main thread**: runs the tick loop (reads mic frames, routes to VAD)
- **Background thread**: one per response cycle (STT → LLM → TTS → playback)
- **Mic callback thread**: managed by sounddevice, pushes frames to queue

## Module Map

| Module | File | Responsibility |
|--------|------|----------------|
| Config | `src/chatterbox/config.py` | Load personality config TOML |
| State | `src/chatterbox/state.py` | State enum, transition rules, timeout |
| Pipeline | `src/chatterbox/pipeline.py` | Orchestrator, main loop |
| Mic | `src/chatterbox/audio/mic.py` | Sounddevice input stream |
| Speaker | `src/chatterbox/audio/speaker.py` | Sounddevice output |
| VAD | `src/chatterbox/audio/vad.py` | Silero-VAD speech boundary detection |
| STT | `src/chatterbox/stt/transcriber.py` | whisper.cpp subprocess wrapper |
| LLM | `src/chatterbox/llm/engine.py` | Ollama streaming chat |
| Context | `src/chatterbox/llm/context.py` | Conversation history |
| TTS | `src/chatterbox/tts/synthesizer.py` | Piper sentence-buffered synthesis |

## Key Design Decisions

1. **Batch STT** — VAD collects a full utterance, then whisper transcribes it. Better quality than streaming.
2. **Streaming LLM → TTS** — LLM streams tokens; TTS buffers until sentence boundary, synthesizes and plays each sentence while later ones generate.
3. **800ms silence timeout** — Configurable balance between responsiveness and false turn-end detection.
4. **whisper.cpp via subprocess** — Thin wrapper saves WAV, calls CLI, parses stdout. Avoids fragile Python bindings.
