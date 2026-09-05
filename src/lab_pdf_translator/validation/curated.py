"""Reglas relacionales específicas del contrato Curated."""
from __future__ import annotations
from typing import Any
from .issues import ValidationIssue
def validate_curated_semantics(doc: dict[str,Any], raw: dict[str,Any]) -> tuple[ValidationIssue,...]:
 ids={s["span_id"] for p in raw["pages"] for b in p["blocks"] for l in b["lines"] for s in l["spans"]}; pages={p["page_id"] for p in raw["pages"]}; blocks={b["block_id"] for p in raw["pages"] for b in p["blocks"]}; lines={l["line_id"] for p in raw["pages"] for b in p["blocks"] for l in b["lines"]}; seen=set(); issues=[]
 for i,u in enumerate(doc.get("units",[])):
  path=f"$.units[{i}]"; uid=u.get("unit_id")
  if uid in seen: issues.append(ValidationIssue("DUPLICATE_CURATED_ID",path,"unit_id must be unique"))
  seen.add(uid)
  for key,available in (("span_ids",ids),("line_ids",lines),("block_ids",blocks),("page_ids",pages)):
   for value in u.get("source",{}).get(key,[]):
    if value not in available: issues.append(ValidationIssue("BROKEN_PROVENANCE",path+".source."+key,f"unknown RAW id {value}"))
  if u.get("type")!="image_reference" and not u.get("source",{}).get("span_ids"): issues.append(ValidationIssue("MISSING_PROVENANCE",path,"text unit needs source spans"))
  if u.get("type") in {"code_block","header","footer","page_number"} and u.get("translatable"): issues.append(ValidationIssue("INVALID_TRANSLATABLE",path,"technical/structural unit must not be translatable"))
  if not isinstance(u.get("confidence"), (int, float)) or not 0 <= u["confidence"] <= 1: issues.append(ValidationIssue("INVALID_CONFIDENCE",path,"confidence must be 0..1"))
  if not isinstance(u.get("classification_signals"), list) or not u["classification_signals"]: issues.append(ValidationIssue("MISSING_CLASSIFICATION_SIGNALS",path,"classification signals required"))
  if not u.get("semantic_type") or not u.get("document_role") or not u.get("classification_family"): issues.append(ValidationIssue("MISSING_CLASSIFICATION_FAMILY",path,"semantic type, role and family required"))
  if not isinstance(u.get("reading_order_confidence"), (int, float)) or not 0 <= u["reading_order_confidence"] <= 1: issues.append(ValidationIssue("INVALID_READING_ORDER_CONFIDENCE",path,"reading-order confidence must be 0..1"))
  if u.get("page_reference") is not None:
   if u.get("document_role") not in {"toc_entry","index_entry"} or u.get("type") == "page_number": issues.append(ValidationIssue("INVALID_PAGE_REFERENCE",path,"navigation reference must remain distinct from page_number"))
   if not u.get("page_reference_source_span_ids") or any(value not in ids for value in u["page_reference_source_span_ids"]): issues.append(ValidationIssue("BROKEN_PAGE_REFERENCE_PROVENANCE",path,"page reference span IDs must resolve"))
   if not any(segment.get("protected") and u["page_reference"] in segment.get("text", "") for segment in u.get("segments", [])): issues.append(ValidationIssue("UNPROTECTED_PAGE_REFERENCE",path,"page reference must be protected"))
  if u.get("document_role") == "technical_value" and (u.get("translatable") or not u.get("segments") or not all(segment.get("protected") for segment in u["segments"])): issues.append(ValidationIssue("UNSAFE_TECHNICAL_VALUE",path,"isolated technical value must be fully protected and non-translatable"))
  if u.get("type") == "code_block":
   code_lines=u.get("lines")
   if not isinstance(code_lines,list) or "\n".join(code_lines) != u.get("text"): issues.append(ValidationIssue("INVALID_CODE_LINES",path,"code lines must reconstruct exact code text"))
  for segment in u.get("segments", []):
   if not segment.get("source_span_ids"): issues.append(ValidationIssue("MISSING_SEGMENT_PROVENANCE",path,"segment must retain source span"))
 return tuple(issues)
