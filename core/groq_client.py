"""Groq LLM interaction.

The original ``ask_groq`` used a module-global Groq client and the hardcoded
TASK_INSTRUCTIONS constant. Here the client is built per call from a passed key and
the instructions (the system prompt) are a parameter - this is what lets the web UI
send a chosen/edited template as the instructions for each request.

Truncation is returned as a flag on the result instead of being printed to stderr,
so the caller (CLI or API) decides how to surface it.
"""

from dataclasses import dataclass

from groq import Groq

from .config import DEFAULT_GROQ_MODEL, DEFAULT_MAX_TOKENS


@dataclass
class GroqResult:
    text: str
    truncated: bool  # True when finish_reason == "length" (output hit max_tokens)
    model: str


def build_groq_client(api_key: str) -> Groq:
    """Create a Groq client for a single request. Kept tiny and separate so tests
    can patch it and callers never share a module-global client."""
    return Groq(api_key=api_key)


def ask_groq(
    client: Groq,
    instructions: str,
    issue_key: str,
    summary: str,
    description: str,
    *,
    model: str = DEFAULT_GROQ_MODEL,
    max_tokens: int = DEFAULT_MAX_TOKENS,
) -> GroqResult:
    """Send the ticket to Groq using ``instructions`` as the system prompt."""
    user_message = (
        f"Ticket: {issue_key}\n"
        f"Summary: {summary}\n\n"
        f"Description:\n{description or '(no description provided)'}"
    )
    response = client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": instructions},
            {"role": "user", "content": user_message},
        ],
    )
    choice = response.choices[0]
    return GroqResult(
        text=choice.message.content,
        truncated=choice.finish_reason == "length",
        model=model,
    )
