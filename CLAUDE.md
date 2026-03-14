# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a **Hebrew-language voice command reformulation system**. It takes spoken user utterances and converts them into standardized, canonical commands for a voice assistant — designed for elderly users.

## Running the Script

```bash
python command_reformulatuin_script.py "<utterance>" <intent>
```

- `<utterance>`: Hebrew text (e.g., `"תשלחי הודעה לישראל שאני מאחרת"`)
- `<intent>`: Integer 0–9 (see intent map below)

The script has no build step, test suite, or linter configured. Dependencies must be installed manually via pip: `transformers`, `torch`, `pandas`, `python-Levenshtein`, `tokenizers`.

## Intent Map

| ID | Intent |
|----|--------|
| 0 | `call` |
| 1 | `alarm` |
| 2 | `sms` |
| 3 | `search_query` |
| 4 | `navigation` |
| 5 | `calendar` |
| 6 | `camera` |
| 7 | `weather` |
| 8 | `notes` |
| 9 | `flashlight` |

## Architecture

The entire system lives in `command_reformulatuin_script.py` (~1,256 lines). The `intent_model/` directory contains a fine-tuned `BertForSequenceClassification` model (99.61% accuracy, 10 classes).

**Processing pipeline:**

```
Hebrew utterance
    → NER extraction (heBERT_NER primary, DictaBERT-NER fallback)
    → Intent-specific handler (call_command, sms_command, alarm_command, etc.)
    → create_command() normalization
    → Standardized Hebrew command string
```

**Key architectural patterns:**

- **Two NER pipelines in sequence**: `avichr/heBERT_NER` first, `dicta-il/dictabert-ner` as fallback for entity extraction (PERSON, LOCATION, TIME/DATE).
- **Global Hebrew lexical sets**: Hard-coded dictionaries of Hebrew time words, days, months, question words used for keyword matching.
- **Fuzzy matching via Levenshtein distance**: Thresholds of <2 or <3 edit distance to strip meta-words and filler from speech recognition output; handles spelling variation and ASR errors.
- **Template-based command generation**: Each intent builds a list of slots, then `create_command()` joins and normalizes them. Templates are truncated dynamically when slots are empty.
- **Hebrew-specific normalization**: Strips preposition prefixes (`ב`, `ל`), handles double-letter edge cases (e.g., `לל` → `ל`), with special-cased city names like `בני ברק`.
- **Character offset tracking**: `end_point` tracks entity end positions to extract remaining text after a named entity.
