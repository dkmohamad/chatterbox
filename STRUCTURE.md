# Chatterbox — Project Structure

```
chatterbox/
├── pyproject.toml                 # package definition + dependencies
├── .gitignore
├── STRUCTURE.md                   # this file
├── TODO.md                        # build progress tracker
├── config/
│   └── chatterbox.toml            # all configuration in one file
├── src/chatterbox/
│   ├── __init__.py
│   ├── __main__.py                # entry point: python -m chatterbox
│   ├── config.py                  # TOML config loading
│   ├── state.py                   # state machine (IDLE/LISTENING/THINKING/SPEAKING)
│   ├── pipeline.py                # orchestrator — wires all modules, runs main loop
│   ├── audio/
│   │   ├── mic.py                 # sounddevice mic capture → queue of 30ms PCM frames
│   │   ├── speaker.py             # sounddevice playback (streaming from TTS)
│   │   └── vad.py                 # silero-vad speech boundary detection
│   ├── wake/
│   │   └── detector.py            # openwakeword wake word detection
│   ├── stt/
│   │   └── transcriber.py         # whisper.cpp subprocess wrapper
│   ├── llm/
│   │   ├── engine.py              # Ollama streaming chat
│   │   └── context.py             # conversation history (max_turns, clear on timeout)
│   └── tts/
│       └── synthesizer.py         # piper-tts sentence-buffered synthesis
├── models/                        # downloaded at first run (.gitignored)
│   ├── whisper/                   # e.g. ggml-base.en.bin
│   └── piper/                     # e.g. en_US-amy-medium.onnx + .json
└── tests/
    ├── test_state.py
    ├── test_context.py
    └── test_smoke.py
```

## Data Flow

```
Mic (16kHz) → [IDLE] WakeWordDetector → wake detected → [LISTENING] VAD
                                                            ↓
                                                      speech ends
                                                            ↓
                                                    Transcriber (whisper.cpp)
                                                            ↓
                                                    CharacterEngine (Ollama) → streams tokens
                                                            ↓
                                                    Synthesizer (piper) → buffers sentences
                                                            ↓
                                                    Speaker → audio out
                                                            ↓
                                                    → back to LISTENING
```

## Threading Model

- **Main thread**: tick loop (wake word detection + VAD processing)
- **Background thread**: one per response cycle (STT → LLM → TTS → playback)
- **Mic callback thread**: managed by sounddevice, pushes frames to queue
