from dataclasses import dataclass
from pathlib import Path
import logging
import tomllib

log = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = "config/momo.toml"


@dataclass
class ChatterboxConfig:
    # Audio
    sample_rate: int = 16000
    frame_ms: int = 30
    input_device: str | int | None = None   # mic (index or name substring)
    output_device: str | int | None = None  # speaker (index or name substring)

    # VAD
    vad_threshold: float = 0.5
    silence_timeout_ms: int = 800

    # STT
    whisper_binary: str = "vendor/whisper.cpp/build/bin/whisper-cli"
    whisper_model_path: str = "models/whisper/ggml-base.en.bin"
    whisper_language: str = "en"

    # LLM
    ollama_model: str = "llama3.2:3b"
    ollama_host: str = "http://localhost:11434"
    system_prompt: str = ""

    # TTS
    piper_model_path: str = "models/piper/en_US-amy-medium.onnx"
    tts_length_scale: float = 1.0
    tts_pitch_semitones: float = 0.0
    tts_croak: float = 0.0       # raspy/gravelly texture (0.0-1.0)
    tts_tremolo: float = 0.0     # wobbly/quivery voice (0.0-1.0)

    # Session
    idle_timeout_s: float = 60.0
    max_turns: int = 20


# Maps TOML section.key to ChatterboxConfig field name
_TOML_MAP: dict[tuple[str, str], str] = {
    ("audio", "sample_rate"): "sample_rate",
    ("audio", "frame_ms"): "frame_ms",
    ("audio", "input_device"): "input_device",
    ("audio", "output_device"): "output_device",
    ("vad", "threshold"): "vad_threshold",
    ("vad", "silence_timeout_ms"): "silence_timeout_ms",
    ("stt", "whisper_binary"): "whisper_binary",
    ("stt", "whisper_model_path"): "whisper_model_path",
    ("stt", "language"): "whisper_language",
    ("llm", "model"): "ollama_model",
    ("llm", "host"): "ollama_host",
    ("tts", "model_path"): "piper_model_path",
    ("tts", "length_scale"): "tts_length_scale",
    ("tts", "pitch_semitones"): "tts_pitch_semitones",
    ("tts", "croak"): "tts_croak",
    ("tts", "tremolo"): "tts_tremolo",
    ("session", "idle_timeout_s"): "idle_timeout_s",
    ("session", "max_turns"): "max_turns",
}


def load_config(config_path: str | None = None) -> ChatterboxConfig:
    """Load all configuration from a single TOML file.

    Resolution order:
    1. Built-in defaults (dataclass)
    2. TOML config file overrides
    """
    config = ChatterboxConfig()

    path = Path(config_path or DEFAULT_CONFIG_PATH)
    if not path.exists():
        log.warning("Config file not found at %s — using defaults", path)
        return config

    with open(path, "rb") as f:
        data = tomllib.load(f)

    # Apply section.key -> field mappings
    for (section, key), field_name in _TOML_MAP.items():
        section_data = data.get(section, {})
        if key in section_data:
            value = section_data[key]
            current = getattr(config, field_name)
            # Coerce type if current value is not None
            if current is not None:
                value = type(current)(value)
            setattr(config, field_name, value)

    # Load personality prompt
    personality = data.get("personality", {})
    prompt = personality.get("prompt", "")
    if prompt:
        config.system_prompt = prompt

    log.info("Config loaded from %s", path)
    return config
