from chatterbox.llm.context import ConversationContext


class TestConversationContext:
    def test_empty_context(self):
        ctx = ConversationContext()
        msgs = ctx.get_messages("You are helpful.")
        assert len(msgs) == 1
        assert msgs[0]["role"] == "system"

    def test_add_user_and_assistant(self):
        ctx = ConversationContext()
        ctx.add_user("Hello")
        ctx.add_assistant("Hi there!")
        msgs = ctx.get_messages("sys")
        assert len(msgs) == 3
        assert msgs[1] == {"role": "user", "content": "Hello"}
        assert msgs[2] == {"role": "assistant", "content": "Hi there!"}

    def test_trim_to_max_turns(self):
        ctx = ConversationContext(max_turns=2)
        for i in range(5):
            ctx.add_user(f"q{i}")
            ctx.add_assistant(f"a{i}")
        # Should keep last 4 messages (2 turns * 2)
        assert len(ctx.messages) == 4
        assert ctx.messages[0]["content"] == "q3"
        assert ctx.messages[-1]["content"] == "a4"

    def test_clear(self):
        ctx = ConversationContext()
        ctx.add_user("Hello")
        ctx.add_assistant("Hi")
        ctx.clear()
        assert len(ctx.messages) == 0
        msgs = ctx.get_messages("sys")
        assert len(msgs) == 1

    def test_system_prompt_always_first(self):
        ctx = ConversationContext()
        ctx.add_user("test")
        msgs = ctx.get_messages("You are Momo.")
        assert msgs[0]["content"] == "You are Momo."
        assert msgs[0]["role"] == "system"
