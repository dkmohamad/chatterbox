# Chatterbox — Build Progress

## Phase 1: Scaffold
- [x] Create project directory structure
- [x] Write pyproject.toml with dependencies
- [x] Set up Python venv and install deps
- [x] Create .gitignore
- [x] Consolidate all config into `config/chatterbox.toml`

## Phase 2: Core Modules
- [x] State machine (`state.py`)
- [x] Mic capture (`audio/mic.py`)
- [x] Speaker playback (`audio/speaker.py`)
- [x] Wake word detector (`wake/detector.py`)
- [x] VAD (`audio/vad.py`)
- [x] STT transcriber (`stt/transcriber.py`)
- [x] LLM engine (`llm/engine.py`)
- [x] Conversation context (`llm/context.py`)
- [x] TTS synthesizer (`tts/synthesizer.py`)

## Phase 3: Integration
- [x] Pipeline orchestrator (`pipeline.py`)
- [x] Entry point (`__main__.py`)
- [x] Build whisper.cpp from source with CUDA (`vendor/whisper.cpp`)
- [x] Install Ollama + pull model
- [x] Download openwakeword models
- [x] End-to-end smoke test — wake word detected (score=0.87)
- [x] First successful full conversation (wake → speech → reply → playback)

## Phase 4: Bugs & Fixes
- [x] VAD chunk size: silero-vad requires exactly 512 samples — added internal buffer
- [x] TTS API: PiperVoice.synthesize() returns AudioChunk, not wave — fixed
- [x] Utterance truncation: start of speech clipped — added 300ms pre-roll buffer
- [ ] Verify pre-roll fix resolves "talk to me" → "to me" truncation

## Phase 5: Configuration & Tuning
- [x] Configurable audio devices (input/output)
- [x] TTS voice pitch/speed controls (length_scale, pitch_semitones)
- [x] Switched TTS voice to `en_GB-semaine-medium`
- [x] Upgraded LLM from `llama3.2:3b` to `phi3.5`
- [x] Simplified personality prompt (pet-like companion, short responses)
- [x] Lowered VAD threshold to 0.3 for better sensitivity

## Phase 6: Documentation
- [x] README.md (links to docs/)
- [x] docs/usage.md — usage, config, voice/model guide
- [x] docs/architecture.md — system design and data flow
- [x] docs/dependencies.md — all deps documented
- [x] docs/troubleshooting.md — common issues and fixes
- [x] STRUCTURE.md — project layout
- [x] setup.sh — one-shot setup script
- [x] Voice changing guide (Piper voices from HuggingFace)
- [x] LLM model guide (Ollama models, VRAM requirements)

## Phase 7: Testing
- [x] State machine tests (17/17 passing)
- [x] Context module tests (5/5 passing)
- [ ] Smoke test (component loading verification)
- [ ] End-to-end conversation test

## Ideas / Future
- [ ] Ebook reader mode — read a PDF/TXT aloud in a different voice
- [ ] Custom wake word training (currently limited to built-in models)
- [ ] Barge-in / interruption support (stop speaking when user talks)
- [ ] Audio feedback (chime on wake word detection)

## Issues Encountered & Fixed
- openwakeword needs `--no-deps` on Python 3.12+ (tflite-runtime unavailable)
- openwakeword models must be explicitly downloaded (`utils.download_models()`)
- silero-vad now requires torchaudio
- torch/torchaudio must be installed from GPU-specific index URL
- whisper.cpp built from source in `vendor/` with CUDA support
- Config consolidated into single `config/chatterbox.toml` (was split across TOML + env vars)
- Utterance truncation caused by VAD needing ~200ms to confirm speech start — fixed with pre-roll buffer
