import logging
from enum import Enum, auto

import numpy as np
import torch

log = logging.getLogger(__name__)

# Silero-VAD minimum chunk size: sr / 31.25 = 512 samples at 16kHz
_MIN_CHUNK_SAMPLES = 512


class VADEvent(Enum):
    SILENCE = auto()
    SPEECH_START = auto()
    SPEECH_CONTINUES = auto()
    SPEECH_END = auto()


class VoiceActivityDetector:
    """Silero-VAD based speech boundary detection."""

    def __init__(
        self,
        threshold: float = 0.5,
        silence_timeout_ms: int = 800,
        min_speech_ms: int = 200,
        sample_rate: int = 16000,
        frame_ms: int = 30,
    ):
        self.threshold = threshold
        self.sample_rate = sample_rate
        self.frame_ms = frame_ms

        # Convert ms to frame counts
        self._silence_frames = silence_timeout_ms // frame_ms
        self._min_speech_frames = min_speech_ms // frame_ms

        self._model = None
        self._in_speech = False
        self._speech_frame_count = 0
        self._silence_frame_count = 0
        self._buffer = np.array([], dtype=np.float32)

    def load(self) -> None:
        self._model, _ = torch.hub.load(
            "snakers4/silero-vad",
            "silero_vad",
            trust_repo=True,
        )
        log.info("Silero VAD loaded")

    def process_frame(self, frame: np.ndarray) -> VADEvent:
        """Process a single audio frame. Returns a VADEvent.

        Internally buffers frames and feeds exactly 512 samples at a time
        to silero-vad (its required chunk size at 16kHz).
        """
        # Convert int16 to float32 in [-1, 1] and accumulate
        float_frame = frame.astype(np.float32) / 32768.0
        self._buffer = np.concatenate([self._buffer, float_frame])

        if len(self._buffer) < _MIN_CHUNK_SAMPLES:
            # Not enough data yet — return current state
            if self._in_speech:
                return VADEvent.SPEECH_CONTINUES
            return VADEvent.SILENCE

        # Process exactly 512 samples, keep the remainder
        chunk = self._buffer[:_MIN_CHUNK_SAMPLES]
        self._buffer = self._buffer[_MIN_CHUNK_SAMPLES:]

        audio = torch.from_numpy(chunk)
        confidence = self._model(audio, self.sample_rate).item()
        is_speech = confidence >= self.threshold

        if not self._in_speech:
            if is_speech:
                self._speech_frame_count += 1
                if self._speech_frame_count >= self._min_speech_frames:
                    self._in_speech = True
                    self._silence_frame_count = 0
                    log.debug("Speech started (confidence=%.2f)", confidence)
                    return VADEvent.SPEECH_START
            else:
                self._speech_frame_count = 0
            return VADEvent.SILENCE
        else:
            if is_speech:
                self._silence_frame_count = 0
                return VADEvent.SPEECH_CONTINUES
            else:
                self._silence_frame_count += 1
                if self._silence_frame_count >= self._silence_frames:
                    self._in_speech = False
                    self._speech_frame_count = 0
                    self._silence_frame_count = 0
                    log.debug("Speech ended")
                    return VADEvent.SPEECH_END
                return VADEvent.SPEECH_CONTINUES

    def reset(self) -> None:
        self._in_speech = False
        self._speech_frame_count = 0
        self._silence_frame_count = 0
        self._buffer = np.array([], dtype=np.float32)
        if self._model is not None:
            self._model.reset_states()
