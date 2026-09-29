"""Shared fake objects that mirror the LiteLLM/OpenAI response shape.

These fakes are what every external LLM provider call resolves to during
tests. They are deterministic and never touch the network.
"""


class FakeMsg:
    def __init__(self, content: str):
        self.content = content


class FakeChoice:
    def __init__(self, content: str):
        self.message = FakeMsg(content)


class FakeUsage:
    def __init__(self, prompt: int = 10, completion: int = 20):
        self.prompt_tokens = prompt
        self.completion_tokens = completion
        self.total_tokens = prompt + completion


class FakeResponse:
    def __init__(self, content: str = "ok", usage: FakeUsage | None = None):
        self.choices = [FakeChoice(content)]
        self.usage = usage if usage is not None else FakeUsage()


class FakeHttpError(Exception):
    """Transport/HTTP error thrown by providers (429/500/401...)."""

    def __init__(self, message: str, status_code: int | None = None, retry_after=None):
        super().__init__(message)
        self.status_code = status_code
        self.retry_after = retry_after
