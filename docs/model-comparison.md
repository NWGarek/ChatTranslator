# Model comparison: gemma3:4b vs qwen2.5:7b

Both models translated the made-up sample (`tests/fixtures/made-up-sample.json`,
20 messages in Polish, Ukrainian, Dutch, English and Romanian) with the same
prompt, on the same laptop: Intel Core Ultra 5 125U, 16 GB RAM, no GPU.
Run on 2026-10-20 with `python -m chat_translator … --model <model>`.

Aya Expanse, a model built for translation, was ruled out before testing: its
CC-BY-NC licence arguably excludes an employer's internal tool.

## Result

**gemma3:4b**, on quality first and speed second. It is the default.

| | gemma3:4b | qwen2.5:7b |
|---|---|---|
| Wall-clock time, 20 messages | 215 s | 264 s |
| Languages labelled correctly | 20 / 20 | 20 / 20 |
| Links kept | all | all |
| Translations that change the meaning | 1 | 6 |

## Quality

Both labelled every language correctly and kept every link, so the difference
is in the Dutch.

**qwen2.5:7b changes the meaning where it matters most to staff.**

- It rewrites the form instructions the bot gave. *"język: polski"* and
  *"language: English"* both become *"taal: Nederlands"*, so staff would think
  the flexwerker was told to fill in the Dutch form.
- It invents form options: *"Inrekening overschrijving"*, *"Mislukte uren"*.
- *"pot sa scriu in romana?"* (may I write in Romanian?) becomes *"kan ik in
  het Nederlands schrijven?"*, which reverses the question.
- *"w ciągu 2 dni roboczych"* (within 2 working days) becomes *"weken weken"*,
  which loses the promise entirely.
- It leaves Ukrainian form options untranslated (*"taal: українська → thema:
  Хвороба"*) and mixes alphabets inside a word (*"coordinатор"*).

**gemma3:4b keeps the meaning, with some clumsy wording.**

- Form paths are translated correctly: *"taal: Pools → onderwerp: Betaling →
  subonderwerp: Vooruitbetaling"*.
- Ukrainian and Romanian come out clean and natural.
- Its weak spots are short phrases. *"ok dzięki"* becomes *"ok dankzij"*, which
  means "thanks to", not "thanks". *"Nie ma za co"* becomes the stilted *"Nee,
  het was mij een genoegen"*. *"zaliczka"* is once *"vergoeding"*, though it is
  *"vooruitbetaling"*, the right word, in the bot's reply.

qwen2.5:7b is better at exactly those short phrases (*"Graag gedaan"*,
*"ok dankjewel"*). But a stilted "thank you" misleads no one, while a wrong form
instruction or a reversed question does.

## Speed

gemma3:4b is about 20% faster: roughly 11 s per message against 13 s. The
largest real export has 216 non-empty messages, so that is about 40 minutes
against 48. Neither is a problem for a one-off run.

## Limits of this comparison

The sample is only 20 messages, written to be clear. Real chats are messier,
with typos, slang and voice-note transcripts. When the real exports run, the
summary's failed count and a spot-check of the sheet are the evidence that
matters.
