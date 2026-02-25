from dataclasses import dataclass, field


@dataclass
class ConversationContext:
    max_turns: int = 20
    messages: list[dict[str, str]] = field(default_factory=list)

    def add_user(self, text: str) -> None:
        self.messages.append({"role": "user", "content": text})
        self._trim()

    def add_assistant(self, text: str) -> None:
        self.messages.append({"role": "assistant", "content": text})
        self._trim()

    def get_messages(self, system_prompt: str) -> list[dict[str, str]]:
        msgs = [{"role": "system", "content": system_prompt}]
        msgs.extend(self.messages)
        return msgs

    def clear(self) -> None:
        self.messages.clear()

    def _trim(self) -> None:
        # Keep last max_turns * 2 messages (user + assistant pairs)
        max_msgs = self.max_turns * 2
        if len(self.messages) > max_msgs:
            self.messages = self.messages[-max_msgs:]
