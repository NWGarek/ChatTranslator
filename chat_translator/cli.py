"""Command line: turn one export into an xlsx."""

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from openpyxl import Workbook
from openpyxl.worksheet.worksheet import Worksheet

from chat_translator.translator import Translator

HEADER = ["role", "original_content", "original_language", "translated_content"]


def main(argv: Sequence[str], translator: Translator) -> None:
    parser = argparse.ArgumentParser(prog="chat_translator")
    parser.add_argument("export", type=Path)
    parser.add_argument("-o", "--output", type=Path, help="where to write the xlsx (default: next to the export)")
    args = parser.parse_args(argv)
    output = args.output or args.export.with_suffix(".xlsx")

    export = json.loads(args.export.read_text(encoding="utf-8"))
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(HEADER)
    for conversation in export["conversations"]:
        for message in conversation["messages"]:
            content = message.get("content") or ""
            if not content.strip():
                append_row(sheet, [message["role"], content, "", ""])
                continue
            # The context window of preceding messages arrives with the local model (#3).
            translation = translator.translate(content, context=())
            append_row(sheet, [message["role"], content, translation.original_language, translation.dutch])
    workbook.save(output)


def append_row(sheet: Worksheet, values: list[str]) -> None:
    """Append a row of text. Every cell is a string, so a message like "=)" never becomes a formula."""
    row = sheet.max_row + 1
    for column, value in enumerate(values, start=1):
        cell = sheet.cell(row=row, column=column, value=value)
        cell.data_type = "s"
