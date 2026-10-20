"""Command line: turn one export into an xlsx."""

import argparse
import json
import re
import sys
from collections.abc import Sequence
from pathlib import Path

from openpyxl import Workbook

from chat_translator.ollama_translator import DEFAULT_MODEL, OllamaTranslator, TranslatorUnavailable
from chat_translator.translator import Message, TranslationFailed, Translator

HEADER = ["role", "original_content", "original_language", "translated_content"]
DUTCH = "nl"
ATTEMPTS = 2
"""A failed translation is retried once."""
URL = re.compile(r"https?://\S+")
CONTEXT_SIZE = 3
"""How many earlier messages of the same conversation go along as context."""

Row = list[str]


def main(argv: Sequence[str], translator: Translator | None = None) -> int:
    """Run the command; returns the exit code. Tests pass their own translator."""
    parser = argparse.ArgumentParser(prog="chat_translator")
    parser.add_argument("export", type=Path)
    parser.add_argument("-o", "--output", type=Path, help="where to write the xlsx (default: next to the export)")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Ollama model to translate with (default: {DEFAULT_MODEL})")
    args = parser.parse_args(argv)

    if translator is None:
        try:
            translator = OllamaTranslator(args.model)
        except TranslatorUnavailable as error:
            print(f"error: {error}", file=sys.stderr)
            return 2

    conversations = read_export(args.export)
    rows, failed = translate(conversations, translator)
    write_sheet(rows, args.output or args.export.with_suffix(".xlsx"))
    return 1 if failed else 0


def read_export(path: Path) -> list[list[Message]]:
    """The export's conversations, each a list of its messages in order."""
    export = json.loads(path.read_text(encoding="utf-8"))
    return [
        [Message(m["role"], m.get("content") or "", id=m.get("id", "")) for m in conversation["messages"]]
        for conversation in export["conversations"]
    ]


def translate(conversations: list[list[Message]], translator: Translator) -> tuple[list[Row], list[Message]]:
    """One row per message, in export order, and the messages that could not be translated."""
    rows: list[Row] = []
    failed: list[Message] = []
    for conversation in conversations:
        earlier: list[Message] = []
        for message in conversation:
            if not message.content.strip():
                rows.append([message.role, message.content, "", ""])
                continue
            language, dutch = translate_message(translator, message, context=earlier[-CONTEXT_SIZE:])
            if dutch is None:
                failed.append(message)
            rows.append([message.role, message.content, language, dutch or ""])
            earlier.append(message)
    return rows, failed


def translate_message(translator: Translator, message: Message, context: Sequence[Message]) -> tuple[str, str | None]:
    """The original language and the Dutch, retrying a failed attempt once.

    The Dutch is None when both attempts failed; the language is then whatever
    the last answer said, or blank if no answer came back.
    """
    language = ""
    for _ in range(ATTEMPTS):
        try:
            translation = translator.translate(message.content, context=context)
        except TranslationFailed:
            continue
        language = translation.original_language
        if language == DUTCH:
            # Staff see Dutch exactly as it was written, never the model's "corrected" version.
            return language, message.content
        if links(translation.dutch) == links(message.content):
            return language, translation.dutch
    return language, None


def links(text: str) -> list[str]:
    """Every URL in the text, in order: a translation must keep them all, unchanged."""
    return [url.rstrip(".,;:!?)*'\"") for url in URL.findall(text)]


def write_sheet(rows: list[Row], path: Path) -> None:
    """Every cell is written as text, so a message like "=)" never becomes a formula."""
    workbook = Workbook()
    sheet = workbook.active
    for row_number, row in enumerate([HEADER, *rows], start=1):
        for column, value in enumerate(row, start=1):
            cell = sheet.cell(row=row_number, column=column, value=value)
            cell.data_type = "s"
    workbook.save(path)
