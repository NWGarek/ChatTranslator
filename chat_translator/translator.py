"""The Translator seam: the one boundary between a message and a translation engine."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Translation:
    language: str
    """The message's original language, as an ISO 639-1 code."""
    translation: str
    """The message rendered in Dutch."""


class Translator(Protocol):
    def translate(self, content: str) -> Translation: ...
