"""Pruebas unitarias del esquema determinista de IDs.

Bitácora: 2026-08-30 - Cobertura inicial de fórmulas y entradas inválidas.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from lab_pdf_translator.models.identifiers import (
    asset_id,
    asset_occurrence_id,
    block_id,
    document_id,
    line_id,
    page_id,
    sha256_bytes,
    sha256_file,
    span_id,
)

SOURCE_SHA = "4c7557600bf41b1317b296aa5e9e0d263e7452fbf2834d0760fb018a0c8df90b"
DOCUMENT_ID = "24bffd9a-1120-537e-94cf-781efe32791f"
PAGE_ID = "acb62141-755c-5031-89fd-bd2a40ba0672"
BLOCK_ID = "28fb9c34-31a8-5814-ba11-4d767da682f4"
LINE_ID = "c716d7b4-6404-5c01-b793-d60d27dc4338"
SPAN_ID = "bdc58f59-dc19-5f15-9da8-861ac427a706"
ASSET_SHA = "7ba451133c403e85ee98073f28fd640bc9aa5000f0d6fce0f0b06ff7ac4cd9c5"
ASSET_ID = f"sha256:{ASSET_SHA}"
OCCURRENCE_ID = "dcb48047-fcea-52a8-ac99-2a602e232a71"


def test_full_identifier_chain_matches_contract_examples() -> None:
    assert sha256_bytes(b"example-pdf") == SOURCE_SHA
    assert document_id(SOURCE_SHA) == DOCUMENT_ID
    assert page_id(DOCUMENT_ID, 1) == PAGE_ID
    assert block_id(PAGE_ID, 1) == BLOCK_ID
    assert line_id(BLOCK_ID, 1) == LINE_ID
    assert span_id(LINE_ID, 1) == SPAN_ID
    assert asset_id(ASSET_SHA) == ASSET_ID
    assert asset_occurrence_id(PAGE_ID, ASSET_ID, 1) == OCCURRENCE_ID


def test_sha256_file_streams_the_same_identity(tmp_path: Path) -> None:
    source = tmp_path / "source.bin"
    source.write_bytes(b"example-pdf")
    assert sha256_file(source) == SOURCE_SHA


@pytest.mark.parametrize("bad_hash", ["", "A" * 64, "0" * 63, "not-a-hash"])
def test_hash_based_identifiers_reject_noncanonical_hashes(bad_hash: str) -> None:
    with pytest.raises(ValueError, match="64 lowercase hexadecimal"):
        document_id(bad_hash)
    with pytest.raises(ValueError, match="64 lowercase hexadecimal"):
        asset_id(bad_hash)


@pytest.mark.parametrize("order", [0, -1, True, 1.5])
def test_order_based_identifiers_require_positive_integers(order: object) -> None:
    with pytest.raises(ValueError, match="greater than or equal to 1"):
        page_id(DOCUMENT_ID, order)  # type: ignore[arg-type]


def test_parent_ids_must_be_uuid_v5() -> None:
    with pytest.raises(ValueError, match="valid UUID"):
        page_id("not-a-uuid", 1)
    with pytest.raises(ValueError, match="UUID v5"):
        page_id("123e4567-e89b-12d3-a456-426614174000", 1)


def test_asset_occurrence_rejects_noncanonical_asset_id() -> None:
    with pytest.raises(ValueError, match="sha256"):
        asset_occurrence_id(PAGE_ID, ASSET_SHA, 1)
