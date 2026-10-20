import sys

from chat_translator.cli import main
from chat_translator.translator import Translation


class NoTranslator:
    """Stand-in until the local model is wired in (#3): leaves language and translation blank."""

    def translate(self, content: str) -> Translation:
        return Translation(language="", translation="")


main(sys.argv[1:], translator=NoTranslator())
