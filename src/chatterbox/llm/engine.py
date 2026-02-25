import logging
from typing import Iterator

import ollama

from chatterbox.llm.context import ConversationContext

log = logging.getLogger(__name__)


class CharacterEngine:
    """Ollama-backed character LLM with streaming responses."""

    def __init__(
        self,
        model: str = "llama3.2:3b",
        system_prompt: str = "",
        ollama_host: str = "http://localhost:11434",
    ):
        self.model = model
        self.system_prompt = system_prompt
        self._client: ollama.Client | None = None
        self._host = ollama_host

    def load(self) -> None:
        self._client = ollama.Client(host=self._host)
        # Verify connectivity
        try:
            self._client.list()
            log.info("Ollama connected at %s, model: %s", self._host, self.model)
        except Exception as e:
            log.error("Cannot connect to Ollama at %s: %s", self._host, e)
            raise

    def respond(
        self,
        user_text: str,
        context: ConversationContext,
    ) -> Iterator[str]:
        """Stream LLM response. Yields text chunks.

        Appends both user and assistant messages to context.
        """
        context.add_user(user_text)
        messages = context.get_messages(self.system_prompt)

        full_response: list[str] = []
        try:
            stream = self._client.chat(
                model=self.model,
                messages=messages,
                stream=True,
            )
            for chunk in stream:
                text = chunk["message"]["content"]
                if text:
                    full_response.append(text)
                    yield text

        except Exception as e:
            log.error("LLM error: %s", e)
            if not full_response:
                error_msg = "I'm having trouble thinking right now."
                full_response.append(error_msg)
                yield error_msg

        context.add_assistant("".join(full_response))
