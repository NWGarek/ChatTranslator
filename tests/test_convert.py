"""An export goes in, the xlsx staff will read comes out.

Every test drives the command end to end with a fake Translator and reads the
written sheet back. Exports are built inline: no real export is ever used.
"""

import itertools
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest
from openpyxl import load_workbook

from chat_translator.cli import main
from chat_translator.translator import Message, Translation, TranslationFailed

HEADER = ["role", "original_content", "original_language", "translated_content"]


Answer = Translation | TranslationFailed


class FakeTranslator:
    """Answers from a script and remembers what it was asked.

    A message's script is one answer, or a list of answers given one per attempt.
    """

    def __init__(self, script: dict[str, Answer | list[Answer]] | None = None) -> None:
        self.script = script or {}
        self.asked: list[str] = []
        self.contexts: dict[str, list[Message]] = {}

    def translate(self, content: str, context: Sequence[Message]) -> Translation:
        attempt = self.asked.count(content)
        self.asked.append(content)
        self.contexts[content] = list(context)
        answers = self.script.get(content, Translation(original_language="xx", dutch=f"NL[{content}]"))
        answer = answers[min(attempt, len(answers) - 1)] if isinstance(answers, list) else answers
        if isinstance(answer, TranslationFailed):
            raise answer
        return answer


_ids = itertools.count(1)


def message(role: str, content: Any) -> dict[str, Any]:
    return {"id": f"msg-{next(_ids)}", "role": role, "content": content}


def write_export(path: Path, *conversations: list[dict[str, Any]]) -> Path:
    export = {"conversations": [{"id": f"c{i}", "messages": msgs} for i, msgs in enumerate(conversations)]}
    path.write_text(json.dumps(export, ensure_ascii=False), encoding="utf-8")
    return path


def read_sheet(path: Path) -> list[list[Any]]:
    sheet = load_workbook(path).active
    return [[cell if cell is not None else "" for cell in row] for row in sheet.iter_rows(values_only=True)]


def test_each_message_becomes_a_row_under_the_four_column_header(tmp_path: Path) -> None:
    export = write_export(
        tmp_path / "export.json",
        [message("user", "Cześć"), message("assistant", "Dzień dobry")],
    )
    translator = FakeTranslator(
        {
            "Cześć": Translation(original_language="pl", dutch="Hoi"),
            "Dzień dobry": Translation(original_language="pl", dutch="Goedendag"),
        }
    )

    main([str(export)], translator=translator)

    assert read_sheet(tmp_path / "export.xlsx") == [
        HEADER,
        ["user", "Cześć", "pl", "Hoi"],
        ["assistant", "Dzień dobry", "pl", "Goedendag"],
    ]


def test_text_that_looks_like_a_formula_stays_text(tmp_path: Path) -> None:
    export = write_export(tmp_path / "export.json", [message("user", "=) dzięki")])
    translator = FakeTranslator({"=) dzięki": Translation(original_language="pl", dutch="=) bedankt")})

    main([str(export)], translator=translator)

    sheet = load_workbook(tmp_path / "export.xlsx").active
    assert [(cell.value, cell.data_type) for cell in sheet[2]] == [
        ("user", "s"),
        ("=) dzięki", "s"),
        ("pl", "s"),
        ("=) bedankt", "s"),
    ]


def test_the_output_path_can_be_chosen(tmp_path: Path) -> None:
    export = write_export(tmp_path / "export.json", [message("user", "Hello")])
    chosen = tmp_path / "elsewhere" / "sheet.xlsx"
    chosen.parent.mkdir()

    main([str(export), "-o", str(chosen)], translator=FakeTranslator())

    assert read_sheet(chosen)[1][:2] == ["user", "Hello"]
    assert not (tmp_path / "export.xlsx").exists()


def test_an_empty_message_keeps_its_row_but_is_never_translated(tmp_path: Path) -> None:
    export = write_export(
        tmp_path / "export.json",
        [message("user", "Hello"), message("assistant", "")],
        [message("user", "   \n"), message("assistant", None), message("user", "Thanks")],
    )
    translator = FakeTranslator(
        {
            "Hello": Translation(original_language="en", dutch="Hallo"),
            "Thanks": Translation(original_language="en", dutch="Bedankt"),
        }
    )

    main([str(export)], translator=translator)

    assert translator.asked == ["Hello", "Thanks"]
    assert read_sheet(tmp_path / "export.xlsx") == [
        HEADER,
        ["user", "Hello", "en", "Hallo"],
        ["assistant", "", "", ""],
        ["user", "   \n", "", ""],
        ["assistant", "", "", ""],
        ["user", "Thanks", "en", "Bedankt"],
    ]


def test_a_message_is_translated_with_the_three_before_it_in_its_own_conversation(tmp_path: Path) -> None:
    export = write_export(
        tmp_path / "export.json",
        [
            message("user", "one"),
            message("assistant", "two"),
            message("user", ""),
            message("assistant", "three"),
            message("user", "four"),
            message("assistant", "five"),
        ],
        [message("user", "other conversation")],
    )
    translator = FakeTranslator()

    main([str(export)], translator=translator)

    assert translator.contexts["one"] == []
    assert translator.contexts["two"] == [Message("user", "one")]
    assert translator.contexts["five"] == [
        Message("assistant", "two"),
        Message("assistant", "three"),
        Message("user", "four"),
    ]
    assert translator.contexts["other conversation"] == []


def test_without_a_running_model_it_stops_before_any_work(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    export = write_export(tmp_path / "export.json", [message("user", "Hello")])
    monkeypatch.setenv("OLLAMA_HOST", "http://127.0.0.1:9")  # nothing listens here

    exit_code = main([str(export)])

    assert exit_code != 0
    assert "Ollama" in capsys.readouterr().err
    assert not (tmp_path / "export.xlsx").exists()


def test_a_model_on_another_machine_is_refused_before_any_work(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    export = write_export(tmp_path / "export.json", [message("user", "Hello")])
    monkeypatch.setenv("OLLAMA_HOST", "https://ollama.example.com")

    exit_code = main([str(export)])

    assert exit_code != 0
    assert "not on this machine" in capsys.readouterr().err
    assert not (tmp_path / "export.xlsx").exists()


def test_a_dutch_message_is_its_own_translation_word_for_word(tmp_path: Path) -> None:
    export = write_export(tmp_path / "export.json", [message("user", "hoe lang duurt dat ongeveer")])
    translator = FakeTranslator(
        {"hoe lang duurt dat ongeveer": Translation(original_language="nl", dutch="Hoe lang duurt dat ongeveer?")}
    )

    main([str(export)], translator=translator)

    assert read_sheet(tmp_path / "export.xlsx")[1] == [
        "user",
        "hoe lang duurt dat ongeveer",
        "nl",
        "hoe lang duurt dat ongeveer",
    ]


def test_a_failed_translation_is_retried_once_then_left_blank_and_the_run_carries_on(tmp_path: Path) -> None:
    export = write_export(
        tmp_path / "export.json",
        [message("user", "flaky"), message("user", "broken"), message("user", "fine")],
    )
    translator = FakeTranslator(
        {
            "flaky": [TranslationFailed("no JSON"), Translation(original_language="en", dutch="wankel")],
            "broken": TranslationFailed("no JSON"),
            "fine": Translation(original_language="en", dutch="goed"),
        }
    )

    exit_code = main([str(export)], translator=translator)

    assert translator.asked == ["flaky", "flaky", "broken", "broken", "fine"]
    assert read_sheet(tmp_path / "export.xlsx")[1:] == [
        ["user", "flaky", "en", "wankel"],
        ["user", "broken", "", ""],
        ["user", "fine", "en", "goed"],
    ]
    assert exit_code != 0


def test_a_run_without_failures_exits_cleanly(tmp_path: Path) -> None:
    export = write_export(tmp_path / "export.json", [message("user", "Hello"), message("user", "")])

    assert main([str(export)], translator=FakeTranslator()) == 0


def test_a_translation_that_breaks_a_link_counts_as_failed(tmp_path: Path) -> None:
    dropped = "Formularz: https://www.nwg.nl/flexwerker-formulieren"
    altered = "Formulario: https://www.nwg.nl/formulieren?lang=es"
    fixed_on_retry = "Form: https://www.nwg.nl/a"
    export = write_export(
        tmp_path / "export.json",
        [message("assistant", dropped), message("assistant", altered), message("assistant", fixed_on_retry)],
    )
    translator = FakeTranslator(
        {
            dropped: Translation(original_language="pl", dutch="Formulier: zie de website"),
            altered: Translation(original_language="es", dutch="Formulier: https://www.nwg.nl/formulieren?lang=nl"),
            fixed_on_retry: [
                Translation(original_language="en", dutch="Formulier: https://www.nwg.nl/"),
                Translation(original_language="en", dutch="Formulier: https://www.nwg.nl/a"),
            ],
        }
    )

    exit_code = main([str(export)], translator=translator)

    assert read_sheet(tmp_path / "export.xlsx")[1:] == [
        ["assistant", dropped, "pl", ""],
        ["assistant", altered, "es", ""],
        ["assistant", fixed_on_retry, "en", "Formulier: https://www.nwg.nl/a"],
    ]
    assert exit_code != 0


def test_the_run_reports_counts_and_failed_ids_but_never_message_text(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    broken = message("user", "Mam problem z wypłatą")
    export = write_export(
        tmp_path / "export.json",
        [message("user", "Mój numer to 0612345678"), message("assistant", "")],
        [message("user", "ik ben ziek vandaag"), broken],
    )
    translator = FakeTranslator(
        {
            "Mój numer to 0612345678": Translation(original_language="pl", dutch="Mijn nummer is 0612345678"),
            "ik ben ziek vandaag": Translation(original_language="nl", dutch="Ik ben ziek vandaag."),
            "Mam problem z wypłatą": TranslationFailed("no JSON"),
        }
    )

    main([str(export)], translator=translator)

    out, err = capsys.readouterr()
    console = out + err
    assert "3/3" in err  # progress over the messages that need translating
    assert "4 messages: 1 translated, 1 Dutch kept as written, 1 empty, 1 failed" in out
    assert f"failed: {broken['id']}" in out
    for text in ["0612345678", "Mój numer", "Mijn nummer", "ziek", "wypłatą"]:
        assert text not in console
