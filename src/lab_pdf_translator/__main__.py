"""CLI de la Fase 1.

Bitácora:
    2026-09-05 - Fase 1: comando ``extract`` y códigos de salida estables.
"""
from __future__ import annotations
import argparse
from pathlib import Path
from lab_pdf_translator.extraction.service import ExtractionError, discover_pdf, extract_pdf

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m lab_pdf_translator")
    sub = parser.add_subparsers(dest="command", required=True)
    extract = sub.add_parser("extract", help="extract a governed RAW dataset")
    extract.add_argument("--input", type=Path)
    extract.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)
    try:
        root = Path.cwd()
        source = discover_pdf(root / "input", args.input)
        document = extract_pdf(root, source, resume=args.resume)
    except ExtractionError as exc:
        print(f"ERROR: {exc}")
        return 2
    print(f"PASS: {document['page_count']} pages, {len(document['assets'])} assets -> data/raw/document.json")
    return 0
if __name__ == "__main__": raise SystemExit(main())
