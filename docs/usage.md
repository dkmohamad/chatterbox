# Usage

## Quick Start

```bash
# First time: run the setup script
./setup.sh

# Activate the venv
source .venv/bin/activate

# Run momo
python -m chatterbox
```

## Running

```bash
# Default (uses config/momo.toml)
python -m chatterbox

# Debug logging (shows VAD scores, transcriptions, state transitions)
python -m chatterbox --debug

# Custom config file
python -m chatterbox --config config/my_config.toml
```

Stop with `Ctrl+C`.

## Interaction

1. Chatterbox starts in **listening** mode, immediately ready for speech
2. Speak naturally — Chatterbox detects when you stop (800ms silence)
3. Chatterbox transcribes, thinks, and speaks a reply
4. Continue the conversation — context is maintained
5. After 60 seconds of silence, conversation context is cleared

## Configuration

Each personality gets its own TOML config file (e.g. `config/momo.toml`).

### Sections

**`[audio]`** — Audio devices and capture settings

```toml
[audio]
sample_rate = 16000       # Hz, must be 16000 for whisper/VAD
frame_ms = 30             # audio frame size in milliseconds
# input_device = "default"  # microphone (device index or name substring)
# output_device = "default" # speaker (device index or name substring)
```

To list available audio devices:

```bash
python -c "import sounddevice; print(sounddevice.query_devices())"
```

You can set devices by index number or by name substring. Examples:

```toml
input_device = 4                     # use device index 4
input_device = "ALC897 Analog"       # match by name
output_device = "pulse"              # use PulseAudio
```

If omitted, the system default input/output devices are used.

**`[vad]`** — Voice activity detection / turn-taking

```toml
[vad]
threshold = 0.5           # speech detection confidence
silence_timeout_ms = 800  # how long to wait after speech stops before processing
```

Lower `silence_timeout_ms` makes Chatterbox more responsive but may cut you off mid-pause. Higher values are more patient. 800ms is a good default.

**`[stt]`** — Speech-to-text (whisper.cpp)

```toml
[stt]
whisper_binary = "vendor/whisper.cpp/build/bin/whisper-cli"
whisper_model_path = "models/whisper/ggml-base.en.bin"
language = "en"
```

**`[llm]`** — Language model (Ollama)

```toml
[llm]
model = "llama3.2:3b"
host = "http://localhost:11434"
```

Any model in the Ollama library works. See [Changing LLM Models](#changing-llm-models) for recommendations.

**`[tts]`** — Text-to-speech (piper)

```toml
[tts]
model_path = "models/piper/en_US-amy-medium.onnx"
length_scale = 1.0        # speech speed (>1 = slower, <1 = faster)
pitch_semitones = 0.0     # pitch shift (+2 = higher/younger, -2 = deeper)
```

To change voice, download a different model and update `model_path`. See [Changing Voices](#changing-voices) below.

**`[session]`** — Conversation session

```toml
[session]
idle_timeout_s = 60.0   # seconds of silence before clearing context
max_turns = 20          # max conversation turns to keep in context
```

**`[personality]`** — Character definition

```toml
[personality]
name = "Momo"
prompt = """
Your character prompt here...
"""
```

## Personalities

To create a new character, create a config file with a different personality and pass it with `--config`.

Example — a storytelling owl:

```toml
# config/luna.toml
# Copy all sections from momo.toml, then change:

[personality]
name = "Luna"
prompt = """
You are Luna, a wise old owl who loves telling stories.
You speak slowly and thoughtfully, often pausing to think.
You weave tales about forests, stars, and gentle adventures.
Keep responses to 2-4 sentences.
"""
```

```bash
python -m chatterbox --config config/luna.toml
```

## Changing Voices

Chatterbox uses [Piper](https://github.com/rhasspy/piper) for text-to-speech. All voices are hosted on Hugging Face at [rhasspy/piper-voices](https://huggingface.co/rhasspy/piper-voices).

Each voice requires two files: an `.onnx` model and its `.onnx.json` config.

### Downloading a voice

```bash
# Set the voice you want
VOICE="en_US-lessac-high"
LANG_PATH="en/en_US/lessac/high"
BASE="https://huggingface.co/rhasspy/piper-voices/resolve/main"

wget -O "models/piper/${VOICE}.onnx" "${BASE}/${LANG_PATH}/${VOICE}.onnx"
wget -O "models/piper/${VOICE}.onnx.json" "${BASE}/${LANG_PATH}/${VOICE}.onnx.json"
```

The URL pattern is: `{lang_family}/{locale}/{speaker}/{quality}/{locale}-{speaker}-{quality}.onnx`

Then update the config:

```toml
[tts]
model_path = "models/piper/en_US-lessac-high.onnx"
```

### Quality tiers

| Quality | Sample Rate | Size | Notes |
|---|---|---|---|
| `x_low` | 16 kHz | ~20 MB | Fastest, robotic |
| `low` | 16 kHz | ~63 MB | Decent |
| `medium` | 22.05 kHz | ~63 MB | Good all-round default |
| `high` | 22.05 kHz | ~114 MB | Best quality, slower |

### Recommended English voices

| Voice | Quality | Gender | Notes |
|---|---|---|---|
| `en_GB-semaine-medium` | medium | M/F | 4 speakers, expressive — current default |
| `en_US-amy-medium` | medium | F | Solid quality |
| `en_US-lessac-high` | high | F | Best single-speaker female |
| `en_US-ryan-high` | high | M | Best single-speaker male |
| `en_US-ljspeech-medium` | medium | F | Classic, clean |
| `en_GB-jenny_dioco-medium` | medium | F | British accent |
| `en_GB-alba-medium` | medium | F | Scottish accent |

Browse all available voices: [huggingface.co/rhasspy/piper-voices/tree/main](https://huggingface.co/rhasspy/piper-voices/tree/main)

### Tuning the voice

Use `length_scale` and `pitch_semitones` to shape the character feel:

```toml
[tts]
model_path = "models/piper/en_US-lessac-high.onnx"
length_scale = 1.1        # slightly slower, more relaxed
pitch_semitones = 2.0     # slightly higher, warmer
```

| Setting | Effect |
|---|---|
| `length_scale = 0.8` | Faster speech |
| `length_scale = 1.2` | Slower, more deliberate |
| `pitch_semitones = +3` | Higher pitch (younger/smaller character) |
| `pitch_semitones = -3` | Deeper pitch (older/larger character) |
| `croak = 0.3` | Raspy/gravelly texture (soft clipping) |
| `croak = 0.7` | Very croaky, toad-like |
| `tremolo = 0.15` | Gentle wobbly/quivery voice |
| `tremolo = 0.4` | Strong wobble, creature-like |

Effects can be combined. Example for a small croaky creature:

```toml
[tts]
pitch_semitones = +3
length_scale = 1.4
croak = 0.3
tremolo = 0.15
```

## Changing LLM Models

Chatterbox uses [Ollama](https://ollama.com) for local LLM inference. Any model in the [Ollama library](https://ollama.com/library) works.

### Managing models

```bash
ollama ls              # list installed models
ollama pull <model>    # download a model
ollama rm <model>      # remove a model
```

### Recommended models for RTX 3060 Ti (8GB VRAM)

| Model | Params | VRAM | Speed | Notes |
|---|---|---|---|---|
| `llama3.2:3b` | 3B | ~3-5 GB | 40+ tok/s | Default — fast, leaves VRAM headroom |
| `llama3.1:8b` | 8B | ~6-8 GB | 70+ tok/s | Best quality that fits 8GB |
| `mistral` | 7B | ~5-7 GB | 100+ tok/s | Fastest 7B option |
| `phi3.5` | 3.8B | ~5-6 GB | 60+ tok/s | Compact, GPT-3.5 class |
| `gemma2:2b` | 2.6B | ~3-5 GB | 45+ tok/s | Lightweight alternative |
| `qwen2.5:3b` | 3B | ~3-5 GB | 50+ tok/s | Good multilingual support |

### Switching models

```bash
# Download the model
ollama pull llama3.1:8b
```

Then update your config:

```toml
[llm]
model = "llama3.1:8b"
```

Smaller models respond faster (lower latency to first token), which matters for natural-feeling conversation.

## Troubleshooting

See [troubleshooting.md](troubleshooting.md).
