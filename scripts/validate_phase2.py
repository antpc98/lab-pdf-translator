"""Fail-closed acceptance check for the published Curated layer."""
from __future__ import annotations
import hashlib, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"src"))
from lab_pdf_translator.validation.schema import load_json, validate_schema
from lab_pdf_translator.validation.curated import validate_curated_semantics
def validate_published(root: Path=ROOT) -> list[str]:
 raw_path=root/"data/raw/document.json"; curated_path=root/"data/curated/document.json"; failures=[]
 if not raw_path.is_file() or not curated_path.is_file(): return ["missing RAW or Curated"]
 raw=load_json(raw_path); curated=load_json(curated_path); issues=(*validate_schema(curated,load_json(root/"schemas/curated-document.schema.json")),*validate_curated_semantics(curated,raw))
 profile_path=root/"data/curated/document-profile.json"
 if not profile_path.is_file(): return ["missing DocumentProfile"]
 profile=load_json(profile_path); issues+=validate_schema(profile,load_json(root/"schemas/document-profile.schema.json"))
 if profile != curated.get("document_profile"): failures.append("DocumentProfile mismatch")
 expected=hashlib.sha256(raw_path.read_bytes()).hexdigest()
 if curated["source_raw"]["sha256"] != expected: failures.append("RAW fingerprint mismatch")
 if curated.get("quality", {}).get("metrics", {}).get("PROTECTED_SEGMENTS") != sum(segment.get("protected", False) for unit in curated["units"] for segment in unit["segments"]): failures.append("protected segment metric mismatch")
 for unit in curated["units"]:
  if unit["type"] == "code_block" and "\n".join(unit.get("lines", [])) != unit["text"]: failures.append(f"code line integrity mismatch: {unit['unit_id']}")
  if unit.get("page_reference") and (unit["type"] == "page_number" or unit.get("semantic_type") != "navigation"): failures.append(f"page reference classification mismatch: {unit['unit_id']}")
 critical=[unit for unit in curated["units"] if unit["text"].strip() in {'keccak256("hello") =','keccak256("hello1") ='}]
 if len(critical)!=2 or any(unit["type"]!="code_block" or unit["translatable"] for unit in critical): failures.append("known technical regression")
 if not any(warning.get("code")=="AMBIGUOUS_READING_ORDER" for warning in curated.get("warnings",[])): failures.append("reading-order uncertainty not instrumented")
 failures.extend(map(str,issues))
 return failures
def main() -> int:
 failures=validate_published()
 if failures: print("RESULT: FAIL\n"+"\n".join(failures[:10])); return 1
 print("PHASE 2 QUALITY GATE\nRESULT: PASS"); return 0
if __name__ == "__main__": raise SystemExit(main())
