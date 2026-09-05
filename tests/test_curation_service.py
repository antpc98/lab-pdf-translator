"""Fase 2: contrato, reproducibilidad e inmutabilidad sobre el RAW real."""
from __future__ import annotations
import hashlib, json
from lab_pdf_translator.curation.service import normalize
from lab_pdf_translator.validation.curated import validate_curated_semantics
from lab_pdf_translator.validation.schema import load_json, validate_schema

def test_real_raw_normalizes_deterministically_without_mutation(project_root, tmp_path) -> None:
    raw_path = project_root / "data/raw/document.json"; before = hashlib.sha256(raw_path.read_bytes()).hexdigest()
    first = normalize(project_root, raw_path, tmp_path / "one.json")
    second = normalize(project_root, raw_path, tmp_path / "two.json")
    assert first == second
    assert hashlib.sha256(raw_path.read_bytes()).hexdigest() == before
    assert not validate_schema(first, load_json(project_root / "schemas/curated-document.schema.json"))
    assert not validate_curated_semantics(first, json.loads(raw_path.read_text(encoding="utf-8")))
    assert first["quality"]["metrics"]["UNITS_WITHOUT_PROVENANCE"] == 0
    assert first["document_profile"]["navigation_families"]
    navigation = [unit for unit in first["units"] if unit["document_role"] in {"toc_entry", "index_entry"}]
    assert navigation and all(unit["page_reference"] and unit["type"] != "page_number" for unit in navigation)
    assert all("reading_order_confidence" in unit for unit in first["units"])
    critical = [unit for unit in first["units"] if unit["text"].strip() in {'keccak256("hello") =', 'keccak256("hello1") ='}]
    assert len(critical) == 2 and all(unit["type"] == "code_block" and not unit["translatable"] for unit in critical)
    assert any(unit["semantic_type"] == "metadata" and unit["document_role"] == "author" for unit in first["units"])

def test_curation_protects_technical_segments_and_merges_lines(project_root, tmp_path) -> None:
    raw = {"document_id":"f4e6e871-9aa4-57ba-bb5f-e2d665aa8d93", "pages":[{"page_id":"1a363e52-865b-59b2-969a-3b48c0a54a62", "page_number":1, "width":600, "height":800, "asset_occurrences":[], "blocks":[{"block_id":"9964e843-b51e-5523-8a5e-bbbd3f117e9d","block_type":"paragraph","bbox":[40,100,500,120],"lines":[{"line_id":"783c3d1d-8c56-573f-a9f9-19f3b2ab7e4a","bbox":[40,100,500,120],"spans":[{"span_id":"bbf29ff6-5f01-5674-94ed-2cda0bbb9cf0","text":"The getTransaction() transac-","font":{"size":10,"family":"Arial","weight":"normal","style":"normal"}}]}],"asset_occurrence_ids":[]},{"block_id":"9740799d-afb2-5461-a0fd-6e29a29dbca2","block_type":"paragraph","bbox":[40,124,500,144],"lines":[{"line_id":"0b7d7fb4-c780-5fd6-a0d7-df2085b34e91","bbox":[40,124,500,144],"spans":[{"span_id":"3df2cb51-6bd6-554f-9f56-30ab1fc6a6d8","text":"tions returns https://example.com","font":{"size":10,"family":"Arial","weight":"normal","style":"normal"}}]}],"asset_occurrence_ids":[]}]}], "assets":[]}
    source = tmp_path / "raw.json"; source.write_text(json.dumps(raw), encoding="utf-8")
    # The independent contract identifies the source as the canonical RAW path, even with a test fixture input.
    curated = normalize(project_root, source, tmp_path / "curated.json")
    unit = curated["units"][0]
    assert unit["text"] == "The getTransaction() transactions returns https://example.com"
    assert {s["text"] for s in unit["segments"] if s["protected"]} == {"getTransaction()", "https://example.com"}

def test_real_page_number_sequence_keeps_index_reference_out(project_root, tmp_path) -> None:
    document = normalize(project_root, project_root / "data/raw/document.json", tmp_path / "curated.json")
    page = {item["page_number"]: item for item in json.loads((project_root / "data/raw/document.json").read_text(encoding="utf-8"))["pages"]}
    page_274 = page[274]["page_id"]
    values = {(unit["text"], unit["type"]) for unit in document["units"] if page_274 in unit["source"]["page_ids"]}
    assert ("256", "page_number") in values
    assert ("130", "page_number") not in values

def test_code_lines_reconstruct_text_and_are_not_translatable(project_root, tmp_path) -> None:
    document = normalize(project_root, project_root / "data/raw/document.json", tmp_path / "curated.json")
    code = [unit for unit in document["units"] if unit["type"] == "code_block"]
    assert code
    assert all("\n".join(unit["lines"]) == unit["text"] and not unit["translatable"] for unit in code)
