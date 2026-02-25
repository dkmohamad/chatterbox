import logging
import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np

log = logging.getLogger(__name__)


class Transcriber:
    """whisper.cpp subprocess wrapper for speech-to-text."""

    def __init__(
        self,
        model_path: str = "models/whisper/ggml-base.en.bin",
        whisper_binary: str = "whisper-cpp",
        language: str = "en",
    ):
        self.model_path = model_path
        self.whisper_binary = whisper_binary
        self.language = language

    def load(self) -> None:
        """Verify the whisper binary and model exist."""
        if not Path(self.model_path).exists():
            log.warning(
                "Whisper model not found at %s — transcription will fail "
                "until the model is downloaded",
                self.model_path,
            )

    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> str:
        """Transcribe a complete utterance. Returns the text."""
        # Write audio to a temporary WAV file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
            with wave.open(tmp, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)  # int16
                wf.setframerate(sample_rate)
                wf.writeframes(audio.astype(np.int16).tobytes())

        try:
            result = subprocess.run(
                [
                    self.whisper_binary,
                    "-m", self.model_path,
                    "-l", self.language,
                    "-f", tmp_path,
                    "--no-timestamps",
                    "-t", "4",  # threads
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                log.error("whisper.cpp failed: %s", result.stderr.strip())
                return ""

            text = result.stdout.strip()
            log.info("Transcription: %s", text)
            return text

        except FileNotFoundError:
            log.error(
                "whisper.cpp binary not found at '%s'. "
                "Install whisper.cpp and ensure it's on PATH.",
                self.whisper_binary,
            )
            return ""
        except subprocess.TimeoutExpired:
            log.error("whisper.cpp timed out")
            return ""
        finally:
            Path(tmp_path).unlink(missing_ok=True)
