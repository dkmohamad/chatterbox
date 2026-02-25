"""Smoke tests — verify each component can be loaded and initialised.

These tests check that models load, binaries exist, and services are
reachable. They do NOT require a microphone or speakers.
"""

import subprocess
import shutil
from pathlib import Path

import pytest
import numpy as np

PROJECT_ROOT = Path(__file__).parent.parent


# ── Config ────────────────────────────────────────────────────────────

class TestConfig:
    def test_load_default_config(self):
        from chatterbox.config import load_config
        config = load_config(str(PROJECT_ROOT / "config" / "momo.toml"))
        assert config.sample_rate == 16000
        assert "Momo" in config.system_prompt or "momo" in config.system_prompt.lower()

    def test_personality_loaded(self):
        from chatterbox.config import load_config
        config = load_config(str(PROJECT_ROOT / "config" / "momo.toml"))
        assert len(config.system_prompt) > 50, "Personality prompt should be substantial"


# ── State Machine ─────────────────────────────────────────────────────

class TestStateMachineSmoke:
    def test_full_cycle(self):
        from chatterbox.state import StateMachine, State
        sm = StateMachine()
        sm.transition(State.THINKING)
        sm.transition(State.SPEAKING)
        sm.transition(State.LISTENING)
        assert sm.state == State.LISTENING


# ── VAD ───────────────────────────────────────────────────────────────

class TestVAD:
    def test_model_loads(self):
        from chatterbox.audio.vad import VoiceActivityDetector
        vad = VoiceActivityDetector()
        vad.load()
        assert vad._model is not None

    def test_silence_returns_silence_event(self):
        from chatterbox.audio.vad import VoiceActivityDetector, VADEvent
        vad = VoiceActivityDetector()
        vad.load()
        # silero-vad needs >= 512 samples at 16kHz
        silence = np.zeros(512, dtype=np.int16)
        event = vad.process_frame(silence)
        assert event == VADEvent.SILENCE


# ── STT ───────────────────────────────────────────────────────────────

class TestSTT:
    def test_whisper_binary_exists(self):
        from chatterbox.config import load_config
        config = load_config(str(PROJECT_ROOT / "config" / "momo.toml"))
        binary = Path(config.whisper_binary)
        if not binary.is_absolute():
            binary = PROJECT_ROOT / binary
        assert binary.exists(), f"whisper binary not found at {binary}"

    def test_whisper_model_exists(self):
        from chatterbox.config import load_config
        config = load_config(str(PROJECT_ROOT / "config" / "momo.toml"))
        model = Path(config.whisper_model_path)
        if not model.is_absolute():
            model = PROJECT_ROOT / model
        assert model.exists(), f"whisper model not found at {model}"

    def test_transcribe_silence(self):
        """Transcribing silence should return empty or whitespace."""
        from chatterbox.config import load_config
        from chatterbox.stt.transcriber import Transcriber
        config = load_config(str(PROJECT_ROOT / "config" / "momo.toml"))

        whisper_binary = config.whisper_binary
        model_path = config.whisper_model_path
        # Resolve relative paths
        if not Path(whisper_binary).is_absolute():
            whisper_binary = str(PROJECT_ROOT / whisper_binary)
        if not Path(model_path).is_absolute():
            model_path = str(PROJECT_ROOT / model_path)

        t = Transcriber(
            model_path=model_path,
            whisper_binary=whisper_binary,
        )
        t.load()
        silence = np.zeros(16000, dtype=np.int16)  # 1 second of silence
        result = t.transcribe(silence)
        # Silence should produce empty or near-empty transcription
        assert len(result.strip()) < 30, f"Unexpected transcription of silence: {result!r}"


# ── LLM ───────────────────────────────────────────────────────────────

class TestLLM:
    def test_ollama_reachable(self):
        from chatterbox.config import load_config
        from chatterbox.llm.engine import CharacterEngine
        config = load_config(str(PROJECT_ROOT / "config" / "momo.toml"))
        engine = CharacterEngine(
            model=config.ollama_model,
            system_prompt=config.system_prompt,
            ollama_host=config.ollama_host,
        )
        try:
            engine.load()
        except ConnectionError:
            pytest.skip("Ollama not running — start with: ollama serve")

    def test_generate_response(self):
        from chatterbox.config import load_config
        from chatterbox.llm.engine import CharacterEngine
        from chatterbox.llm.context import ConversationContext
        config = load_config(str(PROJECT_ROOT / "config" / "momo.toml"))
        engine = CharacterEngine(
            model=config.ollama_model,
            system_prompt=config.system_prompt,
            ollama_host=config.ollama_host,
        )
        try:
            engine.load()
        except ConnectionError:
            pytest.skip("Ollama not running")

        ctx = ConversationContext()
        chunks = list(engine.respond("Say hello in one word.", ctx))
        response = "".join(chunks)
        assert len(response) > 0, "LLM returned empty response"
        assert len(ctx.messages) == 2  # user + assistant


# ── TTS ───────────────────────────────────────────────────────────────

class TestTTS:
    def test_piper_model_exists(self):
        from chatterbox.config import load_config
        config = load_config(str(PROJECT_ROOT / "config" / "momo.toml"))
        model = Path(config.piper_model_path)
        if not model.is_absolute():
            model = PROJECT_ROOT / model
        assert model.exists(), f"Piper model not found at {model}"

    def test_synthesize_text(self):
        from chatterbox.config import load_config
        from chatterbox.tts.synthesizer import Synthesizer
        config = load_config(str(PROJECT_ROOT / "config" / "momo.toml"))
        model_path = config.piper_model_path
        if not Path(model_path).is_absolute():
            model_path = str(PROJECT_ROOT / model_path)

        synth = Synthesizer(model_path=model_path)
        synth.load()
        audio = synth.synthesize("Hello world.")
        assert len(audio) > 0, "TTS produced no audio"
        assert synth.sample_rate > 0


# ── Pipeline (no audio devices) ──────────────────────────────────────

class TestPipelineConfig:
    def test_pipeline_constructs(self):
        """Pipeline object can be created without loading models."""
        from chatterbox.config import load_config
        from chatterbox.pipeline import Pipeline
        config = load_config(str(PROJECT_ROOT / "config" / "momo.toml"))
        pipeline = Pipeline(config)
        assert pipeline.state_machine.state.name == "LISTENING"
