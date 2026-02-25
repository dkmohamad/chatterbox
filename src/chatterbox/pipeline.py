import logging
import threading
from collections import deque

import numpy as np

from chatterbox.audio.mic import MicStream
from chatterbox.audio.speaker import Speaker
from chatterbox.audio.vad import VADEvent, VoiceActivityDetector
from chatterbox.config import ChatterboxConfig
from chatterbox.llm.context import ConversationContext
from chatterbox.llm.engine import CharacterEngine
from chatterbox.stt.transcriber import Transcriber
from chatterbox.state import State, StateMachine
from chatterbox.tts.synthesizer import Synthesizer

log = logging.getLogger(__name__)


class Pipeline:
    """Main orchestrator. Wires all modules and runs the voice agent loop."""

    def __init__(self, config: ChatterboxConfig):
        self.config = config
        self.state_machine = StateMachine(idle_timeout_s=config.idle_timeout_s)

        self.mic = MicStream(
            sample_rate=config.sample_rate,
            frame_ms=config.frame_ms,
            device=config.input_device,
        )
        self.vad = VoiceActivityDetector(
            threshold=config.vad_threshold,
            silence_timeout_ms=config.silence_timeout_ms,
            sample_rate=config.sample_rate,
            frame_ms=config.frame_ms,
        )
        self.stt = Transcriber(
            model_path=config.whisper_model_path,
            whisper_binary=config.whisper_binary,
            language=config.whisper_language,
        )
        self.llm = CharacterEngine(
            model=config.ollama_model,
            system_prompt=config.system_prompt,
            ollama_host=config.ollama_host,
        )
        self.tts = Synthesizer(
            model_path=config.piper_model_path,
            length_scale=config.tts_length_scale,
            pitch_semitones=config.tts_pitch_semitones,
            croak=config.tts_croak,
            tremolo=config.tts_tremolo,
        )
        self.speaker = Speaker(device=config.output_device)
        self.context = ConversationContext(max_turns=config.max_turns)

        self._shutdown = threading.Event()
        self._audio_buffer: list[np.ndarray] = []
        self._response_thread: threading.Thread | None = None

        # Pre-roll buffer: keeps recent frames so we capture the start of
        # speech that the VAD needs to analyse before firing SPEECH_START.
        # ~300ms of pre-roll at 30ms/frame = 10 frames.
        self._pre_roll: deque[np.ndarray] = deque(maxlen=10)

    def load_all(self) -> None:
        """Load all models. Called once at startup."""
        log.info("Loading models...")
        self.vad.load()
        self.stt.load()
        self.llm.load()
        self.tts.load()
        self.speaker.sample_rate = self.tts.sample_rate
        log.info("All models loaded. Ready.")

    def run(self) -> None:
        """Main loop. Blocks until shutdown signal."""
        self.load_all()
        self.mic.start()
        log.info("Listening...")

        try:
            while not self._shutdown.is_set():
                self._tick()
        except KeyboardInterrupt:
            log.info("Keyboard interrupt")
        finally:
            self.mic.stop()
            log.info("Shutdown complete")

    def _tick(self) -> None:
        """Process one audio frame based on current state."""
        frame = self.mic.read_frame(timeout=0.1)
        if frame is None:
            # Still check timeout even with no frame
            if self.state_machine.check_timeout():
                self._handle_timeout()
            return

        match self.state_machine.state:
            case State.LISTENING:
                self._handle_listening(frame)
            case State.THINKING | State.SPEAKING:
                pass  # response running in background thread

    def _handle_listening(self, frame: np.ndarray) -> None:
        """Feed frame to VAD. When speech ends, launch response."""
        # Check timeout
        if self.state_machine.check_timeout():
            self._handle_timeout()
            return

        event = self.vad.process_frame(frame)

        match event:
            case VADEvent.SPEECH_START:
                self.state_machine.touch()
                # Prepend pre-roll frames to capture the start of the utterance
                self._audio_buffer.clear()
                self._audio_buffer.extend(self._pre_roll)
                self._pre_roll.clear()
                self._audio_buffer.append(frame)
            case VADEvent.SPEECH_CONTINUES:
                self.state_machine.touch()
                self._audio_buffer.append(frame)
            case VADEvent.SPEECH_END:
                if self._audio_buffer:
                    audio = np.concatenate(self._audio_buffer)
                    self._audio_buffer.clear()
                    self._launch_response(audio)
            case VADEvent.SILENCE:
                # Keep recent frames in case speech is about to start
                self._pre_roll.append(frame)

    def _handle_timeout(self) -> None:
        """Clear context on conversation timeout, stay in LISTENING."""
        log.info("Conversation timed out — clearing context")
        self.context.clear()
        self.vad.reset()
        self.state_machine.touch()

    def _launch_response(self, audio: np.ndarray) -> None:
        """Launch STT → LLM → TTS → Speaker in a background thread."""
        self.state_machine.transition(State.THINKING)

        def _run() -> None:
            try:
                # Transcribe
                text = self.stt.transcribe(audio, self.config.sample_rate)
                if not text.strip():
                    log.info("Empty transcription — back to listening")
                    self.state_machine.transition(State.SPEAKING)
                    self.state_machine.transition(State.LISTENING)
                    return

                log.info("User: %s", text)

                # Generate response (streaming)
                text_stream = self.llm.respond(text, self.context)

                # Synthesize and play (streaming)
                self.state_machine.transition(State.SPEAKING)
                audio_stream = self.tts.synthesize_stream(text_stream)
                self.speaker.play_stream(audio_stream)

                # Ready for follow-up
                self.state_machine.transition(State.LISTENING)
                self.vad.reset()
                self.state_machine.touch()
                log.info("Ready for follow-up...")

            except Exception:
                log.exception("Error in response pipeline")
                # Try to recover to a valid state
                try:
                    if self.state_machine.state == State.THINKING:
                        self.state_machine.transition(State.SPEAKING)
                    if self.state_machine.state == State.SPEAKING:
                        self.state_machine.transition(State.LISTENING)
                except ValueError:
                    pass

        self._response_thread = threading.Thread(target=_run, daemon=True)
        self._response_thread.start()

    def shutdown(self) -> None:
        """Signal graceful shutdown."""
        self._shutdown.set()
