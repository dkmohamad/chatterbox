import time

import pytest

from chatterbox.state import State, StateMachine


class TestStateMachine:
    def test_initial_state(self):
        sm = StateMachine()
        assert sm.state == State.LISTENING

    def test_valid_transition_listening_to_thinking(self):
        sm = StateMachine()
        sm.transition(State.THINKING)
        assert sm.state == State.THINKING

    def test_valid_transition_thinking_to_speaking(self):
        sm = StateMachine()
        sm.transition(State.THINKING)
        sm.transition(State.SPEAKING)
        assert sm.state == State.SPEAKING

    def test_valid_transition_speaking_to_listening(self):
        sm = StateMachine()
        sm.transition(State.THINKING)
        sm.transition(State.SPEAKING)
        sm.transition(State.LISTENING)
        assert sm.state == State.LISTENING

    def test_invalid_transition_raises(self):
        sm = StateMachine()
        with pytest.raises(ValueError, match="Invalid transition"):
            sm.transition(State.SPEAKING)

    def test_timeout_not_in_listening(self):
        sm = StateMachine(idle_timeout_s=0.01)
        sm.transition(State.THINKING)
        time.sleep(0.02)
        assert not sm.check_timeout()  # in THINKING, not LISTENING

    def test_timeout_in_listening(self):
        sm = StateMachine(idle_timeout_s=0.01)
        time.sleep(0.02)
        assert sm.check_timeout()

    def test_touch_resets_timeout(self):
        sm = StateMachine(idle_timeout_s=0.05)
        time.sleep(0.03)
        sm.touch()
        time.sleep(0.03)
        assert not sm.check_timeout()

    def test_full_conversation_cycle(self):
        sm = StateMachine()
        sm.transition(State.THINKING)
        sm.transition(State.SPEAKING)
        sm.transition(State.LISTENING)
        sm.transition(State.THINKING)
        sm.transition(State.SPEAKING)
        sm.transition(State.LISTENING)
        assert sm.state == State.LISTENING
