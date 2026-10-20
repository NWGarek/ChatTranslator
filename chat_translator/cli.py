"""Command line: turn one export into an xlsx."""

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from openpyxl import Workbook

from chat_translator.translator import Translator

HEADER = ["role", "original_content", "original_language", "translated_content"]


def main(argv: Sequence[str], translator: Translator) -> None:
    parser = argparse.ArgumentParser(prog="chat_translator")
    parser.add_argument("export", type=Path)
    args = parser.parse_args(argv)

    export = json.loads(args.export.read_text(encoding="utf-8"))
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(HEADER)
    for conversation in export["conversations"]:
        for message in conversation["messages"]:
            translated = translator.translate(message["content"])
            sheet.append([message["role"], message["content"], translated.language, translated.translation])
    workbook.save(args.export.with_suffix(".xlsx"))
