import sys
from collections.abc import Sequence

from chat_translator.cli import main
from chat_translator.translator import Message, Translation


class NoTranslator:
    """Stand-in until the local model is wired in (#3): leaves language and translation blank."""

    def translate(self, content: str, context: Sequence[Message]) -> Translation:
        return Translation(original_language="", dutch="")


main(sys.argv[1:], translator=NoTranslator())
