from enum import Enum, auto
import logging
import time

log = logging.getLogger(__name__)

VALID_TRANSITIONS: dict[tuple["State", "State"], bool] = {}


class State(Enum):
    LISTENING = auto()
    THINKING = auto()
    SPEAKING = auto()


# Define valid transitions
_TRANSITIONS = [
    (State.LISTENING, State.THINKING),
    (State.THINKING, State.SPEAKING),
    (State.SPEAKING, State.LISTENING),
]
VALID_TRANSITIONS = {t: True for t in _TRANSITIONS}


class StateMachine:
    def __init__(self, idle_timeout_s: float = 60.0):
        self.state = State.LISTENING
        self.idle_timeout_s = idle_timeout_s
        self._last_activity: float = time.monotonic()

    def transition(self, new_state: State) -> None:
        if (self.state, new_state) not in VALID_TRANSITIONS:
            raise ValueError(
                f"Invalid transition: {self.state.name} -> {new_state.name}"
            )
        log.info("State: %s -> %s", self.state.name, new_state.name)
        self.state = new_state
        self._last_activity = time.monotonic()

    def check_timeout(self) -> bool:
        """Return True if idle timeout elapsed while in LISTENING state."""
        if self.state != State.LISTENING:
            return False
        elapsed = time.monotonic() - self._last_activity
        return elapsed >= self.idle_timeout_s

    def touch(self) -> None:
        """Reset the activity timer (called when speech is detected)."""
        self._last_activity = time.monotonic()
