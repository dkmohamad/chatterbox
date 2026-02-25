# Dependencies

## Python Packages

Declared in `pyproject.toml`:

| Package | Purpose |
|---------|---------|
| sounddevice | Microphone capture and speaker playback via PortAudio |
| numpy | Audio buffer manipulation |
| onnxruntime | ONNX inference backend for openwakeword |
| ollama | Python client for Ollama LLM server |
| piper-tts | Neural text-to-speech synthesis |

Installed separately (require special index URLs or flags):

| Package | Purpose | Notes |
|---------|---------|-------|
| torch | PyTorch for silero-vad model | GPU: `--index-url .../cu128`, CPU: `--index-url .../cpu` |
| torchaudio | Audio processing for silero-vad | Must match torch CUDA version |
| openwakeword | Wake word detection | Installed with `--no-deps` (tflite unavailable on Python 3.12+) |
| scipy, scikit-learn, tqdm, requests | openwakeword runtime deps | Installed explicitly since `--no-deps` skips them |

Dev dependencies (in `pyproject.toml [dev]`):

| Package | Purpose |
|---------|---------|
| pytest | Test runner |
| ruff | Linter and formatter |

## System Dependencies

| Dependency | Purpose | Install |
|------------|---------|---------|
| PortAudio | Audio I/O library | `sudo apt install libportaudio2 portaudio19-dev` |
| Ollama | Local LLM server | `curl -fsSL https://ollama.com/install.sh \| sh` |
| whisper.cpp | Speech-to-text | Built from source in `vendor/whisper.cpp` |
| cmake, build-essential | Build whisper.cpp | `sudo apt install cmake build-essential` |
| CUDA toolkit | GPU acceleration (optional) | Required for GPU whisper.cpp and torch |

## Models

Downloaded by `setup.sh` into gitignored directories:

| Model | Location | Size |
|-------|----------|------|
| whisper ggml-base.en | `models/whisper/ggml-base.en.bin` | ~140 MB |
| piper en_US-amy-medium | `models/piper/en_US-amy-medium.onnx` | ~60 MB |
| openwakeword (hey_jarvis etc.) | Inside venv site-packages | ~10 MB |
| Ollama llama3.2:3b | Managed by Ollama | ~2 GB |
