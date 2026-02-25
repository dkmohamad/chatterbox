import logging
import threading
from typing import Iterator

import numpy as np
import sounddevice as sd

log = logging.getLogger(__name__)


class Speaker:
    """Plays raw PCM audio through the default output device."""

    def __init__(
        self,
        sample_rate: int = 22050,
        device: str | int | None = None,
    ):
        self.sample_rate = sample_rate
        self.device = device
        self._stop_event = threading.Event()

    def play_bytes(self, audio_data: bytes) -> None:
        """Play a single chunk of raw int16 PCM audio."""
        samples = np.frombuffer(audio_data, dtype=np.int16)
        sd.play(samples, samplerate=self.sample_rate, device=self.device, blocking=True)

    def play_stream(self, audio_iter: Iterator[bytes]) -> None:
        """Stream audio chunks to the speaker as they arrive."""
        self._stop_event.clear()
        for chunk in audio_iter:
            if self._stop_event.is_set():
                log.info("Playback interrupted")
                break
            samples = np.frombuffer(chunk, dtype=np.int16)
            sd.play(samples, samplerate=self.sample_rate, device=self.device, blocking=True)

    def stop(self) -> None:
        """Interrupt current playback."""
        self._stop_event.set()
        sd.stop()
