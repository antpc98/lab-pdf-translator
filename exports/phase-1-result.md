# Phase 1 result

PHASE: 1 — Structured RAW Extraction
STATUS: DONE
DATE: 2026-09-05
SOURCE_FILE: mastering-blockchain-unlocking-the-power-of-cryptocurrencies-smart-contracts-and-decentralized-applications-1nbsped-1492054704-9781492054702_compress.pdf
SOURCE_SHA256: cd3662844b88289dec16790e0569f04dd4a00e00a5bd3e60f2b39e916b16bf38
PHYSICAL_PAGES: 284
RAW_PAGES: 284
BLOCKS: 3187
LINES: 9587
SPANS: 13731
ASSETS: 105
ASSET_OCCURRENCES: 153
TESTS: 64 passed
COVERAGE: 90.98%
QUALITY_GATE: PASS
EXIT_CODE: 0

## Implemented

- Automatic or explicit PDF discovery, `python -m lab_pdf_translator extract`, and `run_lab.ps1`.
- PyMuPDF RAW extraction of all physical pages, blocks, lines, spans, typography, geometry, and images.
- SHA-256 / UUIDv5 identity through the Phase 0 identifier module, deterministic geometric ordering, conservative classification, asset deduplication, and occurrence references.
- Checkpointed resume, schema and semantic validation before atomic `document.json` publication, and operational logging.
- Phase 1 checks in the quality-gate script: RAW schema, semantics, asset existence, and asset hashes.

## Modified files

- `README.md`
- `schemas/document.schema.json`
- `scripts/quality_gate.py`

## Created files

- `run_lab.ps1`
- `src/lab_pdf_translator/__main__.py`
- `src/lab_pdf_translator/extraction/service.py`
- `tests/test_cli.py`
- `tests/test_extraction_service.py`

## Validation evidence

`python .venv/Scripts/python.exe scripts/quality_gate.py` returned exit code 0 and `RESULT: PASS`: dependencies, 64 tests, 90.98% coverage, Phase 0 acceptance, RAW schema/semantics, and asset hashes all passed.

## Representative pages reviewed

| Physical page | Blocks | Spans | Image occurrences |
|---:|---:|---:|---:|
| 1 | 4 | 6 | 1 |
| 2 | 1 | 0 | 1 |
| 19 | 8 | 33 | 0 |
| 22 | 7 | 16 | 2 |
| 31 | 12 | 55 | 0 |
| 100 | 13 | 41 | 0 |
| 200 | 9 | 53 | 1 |
| 284 | 5 | 7 | 1 |

## Determinism check

The identifier scheme is exercised by a repeat-extraction test: the same synthetic PDF produces equal document and structural IDs across a clean run and a resumed run. The real extraction uses the same Phase 0 ID functions and source SHA-256. `extracted_at` intentionally remains operational provenance and is not an identity input.

## Resume/interruption check

The suite deliberately interrupts after page 1, resumes from the atomically saved checkpoint, validates the resulting dataset, and compares its structural result with a clean run. Checkpoints are removed after successful publication.

## Warnings

None emitted by the source PDF extraction.

## Known limitations

Block classification is deliberately conservative and does not attempt multicolumn reading order reconstruction, headers/footers suppression, OCR, or editorial normalization. These belong to later phases.

## Remaining work

Proceed with Phase 2 normalization/governance only after choosing its curated-data contract.

## Commands executed

```text
python -m lab_pdf_translator extract --resume
python -m pytest --cov=lab_pdf_translator --cov-report=term-missing
python scripts/quality_gate.py
run_lab.ps1
```
