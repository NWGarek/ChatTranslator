"""The Translator seam: the one boundary between a message and a translation engine."""

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class Message:
    role: str
    """Who wrote it: `user` (the flexwerker) or `assistant` (the bot)."""
    content: str
    id: str = field(default="", compare=False)
    """Chatbase's id: the only way to point at a message without showing its content."""

    @property
    def is_empty(self) -> bool:
        """Blank or whitespace only: it keeps its row but there is nothing to translate."""
        return not self.content.strip()


@dataclass(frozen=True)
class Translation:
    original_language: str
    """The language the message is written in, as an ISO 639-1 code."""
    dutch: str
    """The message rendered in Dutch."""


class TranslationFailed(Exception):
    """This one message could not be translated; the next one may well succeed."""


class Translator(Protocol):
    def translate(self, content: str, context: Sequence[Message]) -> Translation:
        """Translate one message's content, or raise TranslationFailed.

        `context` is the messages just before it in the same conversation. It
        helps make sense of short replies, but is never itself translated and
        never decides the original language.
        """
        ...
