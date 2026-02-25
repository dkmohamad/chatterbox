import logging
import re
from typing import Iterator

import numpy as np
from piper import PiperVoice
from piper.voice import SynthesisConfig

log = logging.getLogger(__name__)

# Sentence-ending punctuation pattern
_SENTENCE_END = re.compile(r"[.!?]\s*$")

# Only allow letters, digits, basic punctuation, and whitespace through to TTS
_ALLOWED = re.compile(r"[^a-zA-Z0-9\s.,!?;:'\"-]")
_MULTI_SPACE = re.compile(r"  +")


def _clean_for_speech(text: str) -> str:
    """Keep only speakable characters — letters, numbers, and basic punctuation."""
    text = _ALLOWED.sub("", text)
    text = _MULTI_SPACE.sub(" ", text)
    return text.strip()


class Synthesizer:
    """Piper TTS with sentence-boundary buffering for streaming synthesis."""

    def __init__(
        self,
        model_path: str,
        length_scale: float = 1.0,
        pitch_semitones: float = 0.0,
        croak: float = 0.0,
        tremolo: float = 0.0,
    ):
        self.model_path = model_path
        self.length_scale = length_scale
        self.pitch_semitones = pitch_semitones
        self.croak = croak
        self.tremolo = tremolo
        self._voice: PiperVoice | None = None
        self._syn_config: SynthesisConfig | None = None

    def load(self) -> None:
        self._voice = PiperVoice.load(self.model_path)
        self._syn_config = SynthesisConfig(length_scale=self.length_scale)
        effects = []
        if self.croak > 0:
            effects.append(f"croak={self.croak:.1f}")
        if self.tremolo > 0:
            effects.append(f"tremolo={self.tremolo:.1f}")
        fx_str = f", fx=[{', '.join(effects)}]" if effects else ""
        log.info(
            "Piper TTS loaded: %s (speed=%.2f, pitch=%+.1f st%s)",
            self.model_path,
            self.length_scale,
            self.pitch_semitones,
            fx_str,
        )

    @property
    def sample_rate(self) -> int:
        if self._voice is None:
            return 22050
        rate = self._voice.config.sample_rate
        if self.pitch_semitones != 0.0:
            # Pitch shifting works by resampling: generate at shifted rate,
            # play back at original rate. The speaker sample_rate stays the
            # same, but we need to resample the audio.
            return rate
        return rate

    def _apply_croak(self, audio: np.ndarray) -> np.ndarray:
        """Add raspy/gravelly texture via soft clipping distortion."""
        if self.croak <= 0.0:
            return audio
        # Work in float64 for precision
        samples = audio.astype(np.float64) / 32768.0
        # Drive controls how hard we push into the soft clip
        drive = 1.0 + self.croak * 8.0
        samples = samples * drive
        # Soft clip using tanh
        samples = np.tanh(samples)
        # Mix dry/wet
        dry = audio.astype(np.float64) / 32768.0
        wet_mix = min(self.croak, 1.0)
        mixed = dry * (1.0 - wet_mix * 0.5) + samples * (wet_mix * 0.5)
        # Normalize back to int16 range
        mixed = np.clip(mixed, -1.0, 1.0)
        return (mixed * 32767).astype(np.int16)

    def _apply_tremolo(self, audio: np.ndarray, sample_rate: int) -> np.ndarray:
        """Add wobbly/quivery amplitude modulation."""
        if self.tremolo <= 0.0:
            return audio
        samples = audio.astype(np.float64)
        # Tremolo at ~5-6 Hz gives a creature-like wobble
        rate_hz = 5.5
        depth = min(self.tremolo, 1.0) * 0.5  # max 50% modulation
        t = np.arange(len(samples)) / sample_rate
        modulator = 1.0 - depth * (1.0 - np.cos(2.0 * np.pi * rate_hz * t))
        samples = samples * modulator
        return np.clip(samples, -32768, 32767).astype(np.int16)

    def _apply_pitch_shift(self, audio: np.ndarray) -> np.ndarray:
        """Shift pitch by resampling. Positive semitones = higher pitch."""
        if self.pitch_semitones == 0.0:
            return audio
        # Pitch shift via resampling: to raise pitch by N semitones,
        # stretch the audio by 2^(N/12) then resample back to original length
        factor = 2.0 ** (self.pitch_semitones / 12.0)
        original_len = len(audio)
        # Resample to new length
        new_len = int(original_len / factor)
        if new_len == 0:
            return audio
        indices = np.linspace(0, original_len - 1, new_len)
        resampled = np.interp(indices, np.arange(original_len), audio.astype(np.float64))
        return resampled.astype(audio.dtype)

    def synthesize(self, text: str) -> bytes:
        """Synthesize a single text string to raw int16 PCM bytes."""
        text = _clean_for_speech(text)
        if not text:
            return b""

        pcm_parts: list[np.ndarray] = []
        for chunk in self._voice.synthesize(text, self._syn_config):
            # chunk.audio_float_array is float32 in [-1, 1]
            audio_int16 = (chunk.audio_float_array * 32767).astype(np.int16)
            pcm_parts.append(audio_int16)

        if not pcm_parts:
            return b""

        audio = np.concatenate(pcm_parts)
        audio = self._apply_pitch_shift(audio)
        audio = self._apply_croak(audio)
        audio = self._apply_tremolo(audio, self._voice.config.sample_rate)
        return audio.tobytes()

    def synthesize_stream(self, text_stream: Iterator[str]) -> Iterator[bytes]:
        """Accept streaming text from LLM, buffer until sentence boundary,
        then yield PCM audio for each complete sentence."""
        buffer = ""

        for chunk in text_stream:
            buffer += chunk

            # Check for sentence boundaries
            while True:
                match = _SENTENCE_END.search(buffer)
                if not match:
                    # Also split on newlines
                    newline_pos = buffer.find("\n")
                    if newline_pos == -1:
                        break
                    sentence = buffer[: newline_pos + 1].strip()
                    buffer = buffer[newline_pos + 1 :]
                else:
                    end = match.end()
                    sentence = buffer[:end].strip()
                    buffer = buffer[end:]

                if sentence:
                    log.debug("Synthesizing: %s", sentence[:60])
                    audio = self.synthesize(sentence)
                    if audio:
                        yield audio

        # Flush remaining text
        remaining = buffer.strip()
        if remaining:
            log.debug("Synthesizing remainder: %s", remaining[:60])
            audio = self.synthesize(remaining)
            if audio:
                yield audio
