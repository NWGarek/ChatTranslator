"""The Translator backed by a local model through Ollama: no message leaves the machine (ADR 0001)."""

import json
import os
import re
from collections.abc import Sequence
from urllib.parse import urlsplit

import httpx
from ollama import Client, ResponseError

from chat_translator.translator import Message, Translation, TranslationFailed

DEFAULT_MODEL = "gemma3:4b"

INSTRUCTIONS = """\
You translate WhatsApp messages into Dutch for Dutch-speaking staff. The messages \
are between flexwerkers (temporary workers) and the company chatbot.

Return JSON with three fields:
- language_name: the English name of the language the message is written in, for \
example "Polish". Judge it from the message alone, never from the earlier messages. \
If the message mixes languages, give the dominant one.
- original_language: the ISO 639-1 code of that same language, for example "pl".
- dutch: the whole message translated into natural Dutch. If it is already Dutch, \
return it unchanged.

Keep URLs exactly as they are. Keep *bold* markers, line breaks, emoji and numbers. \
In paths like "a → b → c", keep the arrows and translate the words.
The earlier messages are context only: do not translate them, do not answer the \
message, and do not add explanations."""

# The model names the language before giving its code: asked for the code
# alone, gemma3:4b labelled Polish messages "nl", confusing the language of the
# message with the language it was translating into.
SCHEMA = {
    "type": "object",
    "properties": {
        "language_name": {"type": "string"},
        "original_language": {"type": "string"},
        "dutch": {"type": "string"},
    },
    "required": ["language_name", "original_language", "dutch"],
}


class TranslatorUnavailable(Exception):
    """The model can't be used, so no work should start."""


ISO_639_1 = re.compile(r"[a-z]{2}")
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}


class OllamaTranslator:
    def __init__(self, model: str = DEFAULT_MODEL) -> None:
        self._model = model
        self._client = Client(host=_local_host())
        try:
            self._client.show(model)
        except ConnectionError as error:
            raise TranslatorUnavailable(f"Cannot reach Ollama. Is it running? ({error})") from error
        except ResponseError as error:
            if error.status_code == 404:
                raise TranslatorUnavailable(
                    f"The model {model} is not pulled into Ollama. Run: ollama pull {model}"
                ) from error
            raise TranslatorUnavailable(f"Ollama cannot use the model {model}: {error.error}") from error

    def translate(self, content: str, context: Sequence[Message]) -> Translation:
        try:
            response = self._client.chat(
                model=self._model,
                messages=[
                    {"role": "system", "content": INSTRUCTIONS},
                    {"role": "user", "content": _prompt(content, context)},
                ],
                format=SCHEMA,
                options={"temperature": 0},
            )
            answer = json.loads(response.message.content or "")
            language = str(answer["original_language"]).strip().lower()
            dutch = str(answer["dutch"])
        # httpx.HTTPError: Ollama dropping out mid-reply surfaces as a raw transport
        # error (read error, timeout), not as the ConnectionError a refused connection gives.
        except (ConnectionError, httpx.HTTPError, ResponseError, ValueError, KeyError, TypeError) as error:
            # The message is not in the error: it must never reach the console.
            raise TranslationFailed(type(error).__name__) from error
        if not ISO_639_1.fullmatch(language):
            raise TranslationFailed("original_language is not an ISO 639-1 code")
        return Translation(original_language=language, dutch=dutch)


def _local_host() -> str:
    """The Ollama address from OLLAMA_HOST, refused unless it is this machine (ADR 0001)."""
    host = os.environ.get("OLLAMA_HOST") or "http://127.0.0.1:11434"
    hostname = urlsplit(host if "://" in host else f"http://{host}").hostname
    if hostname not in LOCAL_HOSTS:
        raise TranslatorUnavailable(
            f"OLLAMA_HOST points to {hostname}, which is not on this machine. "
            "Messages may only be translated locally."
        )
    return host


def _prompt(content: str, context: Sequence[Message]) -> str:
    earlier = "\n".join(f"[{message.role}] {message.content}" for message in context)
    return (
        f"Earlier in this conversation (context only):\n{earlier or '(none)'}\n\n"
        f"Message to translate:\n{content}"
    )
