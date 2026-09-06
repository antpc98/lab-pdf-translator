"""F2 → F3 protected-range contract tests."""
from __future__ import annotations

import json

from lab_pdf_translator.curation.service import _canonical_text_positions, _segments, normalize
from lab_pdf_translator.validation.curated import validate_curated_semantics


def test_protected_ranges_are_exact_and_mask_roundtrip(project_root, tmp_path) -> None:
    document = normalize(project_root, project_root / "data/raw/document.json", tmp_path / "curated.json")
    for unit in document["units"]:
        protected = [segment for segment in unit["segments"] if segment["protected"]]
        assert protected == sorted(protected, key=lambda segment: segment["start"])
        assert all(unit["text"][segment["start"]:segment["end"]] == segment["text"] for segment in protected)
        masked = unit["text"]
        replacements = []
        for ordinal, segment in reversed(list(enumerate(protected, 1))):
            token = f"⟦LPT:{unit['unit_id'][:8]}:{ordinal}⟧"
            replacements.append((token, segment["text"]))
            masked = masked[:segment["start"]] + token + masked[segment["end"]:]
        for token, value in replacements:
            masked = masked.replace(token, value)
        assert masked == unit["text"]


def test_duplicate_values_and_unicode_have_distinct_exact_ranges() -> None:
    lines = [{"spans": [{"span_id": "span", "text": "é hash.a hash.a", "font": {}}]}]
    text, positions = _canonical_text_positions("é hash.a hash.a", False)
    segments = _segments(lines, positions)
    protected = [segment for segment in segments if segment["protected"]]
    assert text == "é hash.a hash.a"
    assert [text[segment["start"]:segment["end"]] for segment in protected] == ["hash.a", "hash.a"]
    assert protected[0]["start"] != protected[1]["start"]


def test_collapsed_leading_whitespace_is_not_a_protected_substring() -> None:
    lines = [{"spans": [{"span_id": "span", "text": "  CTxOut(value=1)", "font": {}}]}]
    text, positions = _canonical_text_positions("  CTxOut(value=1)", False)
    segments = _segments(lines, positions, all_protected=True)
    assert text == "CTxOut(value=1)"
    assert all(segment["protected"] for segment in segments)
    assert all(text[segment["start"]:segment["end"]] == segment["text"] for segment in segments)


def test_validator_rejects_bad_ranges(project_root) -> None:
    raw = json.loads((project_root / "data/raw/document.json").read_text(encoding="utf8"))
    unit = {"unit_id": "x", "type": "paragraph", "text": "abc", "translatable": True,
            "confidence": 1.0, "classification_signals": ["test"], "semantic_type": "body_text",
            "document_role": "paragraph", "classification_family": "test", "reading_order_confidence": 1.0,
            "source": {"page_ids": [], "block_ids": [], "line_ids": [], "span_ids": []},
            "segments": [{"text": "x", "protected": True, "start": -1, "end": 9, "style": {}, "source_span_ids": []}]}
    issues = validate_curated_semantics({"units": [unit]}, raw)
    assert any(issue.code == "INVALID_PROTECTED_RANGE" for issue in issues)
