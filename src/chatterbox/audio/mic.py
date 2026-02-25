import logging
import queue

import numpy as np
import sounddevice as sd

log = logging.getLogger(__name__)


class MicStream:
    """Continuous 16 kHz mono int16 PCM capture."""

    def __init__(
        self,
        sample_rate: int = 16000,
        frame_ms: int = 30,
        device: str | int | None = None,
    ):
        self.sample_rate = sample_rate
        self.frame_size = int(sample_rate * frame_ms / 1000)
        self.device = device
        self.queue: queue.Queue[np.ndarray] = queue.Queue(maxsize=200)
        self._stream: sd.InputStream | None = None

    def start(self) -> None:
        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="int16",
            blocksize=self.frame_size,
            device=self.device,
            callback=self._callback,
        )
        self._stream.start()
        device_info = sd.query_devices(self.device, kind="input")
        log.info(
            "Mic started: %s (%d Hz, %d samples/frame)",
            device_info["name"],
            self.sample_rate,
            self.frame_size,
        )

    def stop(self) -> None:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None
            log.info("Mic stopped")

    def read_frame(self, timeout: float = 1.0) -> np.ndarray | None:
        try:
            return self.queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def _callback(
        self,
        indata: np.ndarray,
        frames: int,
        time_info: object,
        status: sd.CallbackFlags,
    ) -> None:
        if status:
            log.warning("Mic status: %s", status)
        try:
            self.queue.put_nowait(indata[:, 0].copy())
        except queue.Full:
            pass  # drop frame if consumer is behind
