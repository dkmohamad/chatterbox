#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Chatterbox Setup ==="
echo ""

# --- System dependencies ---
echo "[1/8] Checking system dependencies..."

if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found. Install Python 3.11+."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "       Python $PYTHON_VERSION"

if ! dpkg -s libportaudio2 &>/dev/null 2>&1; then
    echo "       Installing PortAudio..."
    sudo apt install -y libportaudio2 portaudio19-dev
else
    echo "       PortAudio OK"
fi

# --- Python venv ---
echo ""
echo "[2/8] Setting up Python venv..."

if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo "       Created .venv"
else
    echo "       .venv already exists"
fi

source .venv/bin/activate

# --- PyTorch (GPU/CPU) ---
echo ""
echo "[3/8] Installing PyTorch..."

if command -v nvidia-smi &>/dev/null; then
    CUDA_VER=$(nvidia-smi | grep -oP 'CUDA Version: \K[0-9]+\.[0-9]+')
    CUDA_MAJOR=$(echo "$CUDA_VER" | cut -d. -f1)
    CUDA_MINOR=$(echo "$CUDA_VER" | cut -d. -f2)
    TORCH_INDEX="cu${CUDA_MAJOR}${CUDA_MINOR}"
    echo "       GPU detected (CUDA $CUDA_VER) — installing for $TORCH_INDEX"
    pip install -q torch torchaudio --index-url "https://download.pytorch.org/whl/${TORCH_INDEX}"
else
    echo "       No GPU detected — installing CPU-only"
    pip install -q torch torchaudio --index-url https://download.pytorch.org/whl/cpu
fi

# --- Python dependencies (from pyproject.toml) ---
echo ""
echo "[4/8] Installing Python dependencies..."

pip install -q -e ".[dev]"
pip install -q openwakeword --no-deps
pip install -q scipy scikit-learn tqdm requests  # openwakeword runtime deps

echo "       Downloading openwakeword models..."
python -c "from openwakeword import utils; utils.download_models()" 2>/dev/null

echo "       Done"

# --- whisper.cpp (build from source with CUDA) ---
echo ""
echo "[5/8] Setting up whisper.cpp..."

WHISPER_DIR="$SCRIPT_DIR/vendor/whisper.cpp"
WHISPER_BIN="$WHISPER_DIR/build/bin/whisper-cli"

if [ -f "$WHISPER_BIN" ]; then
    echo "       Already built at $WHISPER_BIN"
else
    echo "       Cloning and building whisper.cpp..."
    mkdir -p vendor
    if [ ! -d "$WHISPER_DIR" ]; then
        git clone https://github.com/ggerganov/whisper.cpp.git "$WHISPER_DIR"
    fi

    cd "$WHISPER_DIR"

    BUILD_FLAGS="-DWHISPER_BUILD_TESTS=OFF -DWHISPER_BUILD_EXAMPLES=ON"
    if command -v nvidia-smi &>/dev/null; then
        echo "       Building with CUDA support..."
        BUILD_FLAGS="$BUILD_FLAGS -DGGML_CUDA=ON"
    fi

    cmake -B build $BUILD_FLAGS
    cmake --build build --config Release -j$(nproc)
    cd "$SCRIPT_DIR"

    echo "       Built: $WHISPER_BIN"
fi

# --- Whisper model ---
echo ""
echo "[6/8] Downloading whisper model..."

mkdir -p models/whisper
WHISPER_MODEL="models/whisper/ggml-base.en.bin"
if [ ! -f "$WHISPER_MODEL" ]; then
    wget -q --show-progress -O "$WHISPER_MODEL" \
        "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin"
else
    echo "       Already downloaded"
fi

# --- Piper voice model ---
echo ""
echo "[7/8] Downloading piper voice model..."

mkdir -p models/piper
PIPER_MODEL="models/piper/en_US-amy-medium.onnx"
PIPER_JSON="models/piper/en_US-amy-medium.onnx.json"
if [ ! -f "$PIPER_MODEL" ]; then
    wget -q --show-progress -O "$PIPER_MODEL" \
        "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx"
    wget -q --show-progress -O "$PIPER_JSON" \
        "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/amy/medium/en_US-amy-medium.onnx.json"
else
    echo "       Already downloaded"
fi

# --- Ollama ---
echo ""
echo "[8/8] Checking Ollama..."

if ! command -v ollama &>/dev/null; then
    echo "       Installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
fi

echo "       Ollama installed"

# Start Ollama if not running
if ! curl -s http://localhost:11434/api/tags &>/dev/null; then
    echo "       Starting Ollama server..."
    ollama serve &>/dev/null &
    sleep 3
fi

OLLAMA_MODEL=$(python -c "
import tomllib
with open('config/chatterbox.toml', 'rb') as f:
    print(tomllib.load(f)['llm']['model'])
")

if ollama list 2>/dev/null | grep -q "$OLLAMA_MODEL"; then
    echo "       $OLLAMA_MODEL model OK"
else
    echo "       Pulling $OLLAMA_MODEL..."
    ollama pull "$OLLAMA_MODEL"
fi

# --- Update config with correct whisper path ---
echo ""
echo "=== Setup Complete ==="
echo ""
echo "Whisper binary: $WHISPER_BIN"
echo "Update config/chatterbox.toml if needed:"
echo "  [stt]"
echo "  whisper_binary = \"$WHISPER_BIN\""
echo ""
echo "To run Chatterbox:"
echo "  source .venv/bin/activate"
echo "  python -m chatterbox"
echo ""
echo "To run with debug logging:"
echo "  python -m chatterbox --debug"
echo ""
echo "To run tests:"
echo "  pytest -v"
