# Translate with a local model, not a cloud API

Exports are WhatsApp conversations of flexwerkers: personal data. The company Google Cloud account is off-limits, so any cloud translator (DeepL, Claude, OpenAI, a personal Gemini key) would mean sending that data to a processor the employer has no agreement with — and free tiers may train on it. We translate with a local LLM through Ollama instead, so no message ever leaves the machine; the protection comes from the design, not from a promise.

## Considered Options

- **Cloud LLM or DeepL on a personal key** — best quality, but personal data leaves the machine without a processing agreement.
- **Scraping free Google Translate** — brittle, against the terms, and still sends the data out.
- **Local NLLB-200 / Opus-MT plus a language detector** — fast, but detectors fail on very short messages ("multumesc", "Дякую") and quality on informal chat is weaker. A local LLM detects and translates in one call and copes with emoji and language switches.
- **Aya Expanse** — built for translation, but CC-BY-NC; internal company use is arguably commercial.

## Consequences

Translation runs on a CPU-only laptop, so a large export takes on the order of tens of minutes. The volume (a few hundred messages per export) makes that acceptable. The engine sits behind a translator seam, so swapping to an approved cloud service later is one new adapter.
