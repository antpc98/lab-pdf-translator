"""Identificadores deterministas del contrato ``raw``.

Bitácora:
    2026-08-30 - Implementación inicial alineada con ``id_scheme_version = 1``.

La identidad se concentra en este módulo para impedir que extractores, scripts o
pruebas construyan UUID con fórmulas ligeramente diferentes. Todas las funciones
son puras salvo :func:`sha256_file`, que lee un archivo sin modificarlo.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from pathlib import Path

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_ASSET_ID_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_NAME_PREFIX = "lab-pdf-translator"
_READ_CHUNK_SIZE = 1024 * 1024


def sha256_bytes(content: bytes) -> str:
    """Devuelve el SHA-256 hexadecimal y en minúsculas de ``content``."""

    return hashlib.sha256(content).hexdigest()


def sha256_file(path: str | Path) -> str:
    """Calcula SHA-256 por bloques para no cargar documentos grandes en memoria."""

    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(_READ_CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def document_id(source_sha256: str) -> str:
    """Genera el UUID v5 de una versión binaria exacta del documento."""

    _require_sha256(source_sha256, "source_sha256")
    return _uuid5(f"document:sha256:{source_sha256}")


def page_id(parent_document_id: str, page_number: int) -> str:
    """Genera la identidad de una página física numerada desde uno."""

    _require_uuid(parent_document_id, "document_id")
    _require_positive(page_number, "page_number")
    return _uuid5(f"page:{parent_document_id}:{page_number}")


def block_id(parent_page_id: str, block_order: int) -> str:
    """Genera la identidad de un bloque en orden geométrico estable."""

    _require_uuid(parent_page_id, "page_id")
    _require_positive(block_order, "block_order")
    return _uuid5(f"block:{parent_page_id}:{block_order}")


def line_id(parent_block_id: str, line_order: int) -> str:
    """Genera la identidad de una línea dentro de su bloque."""

    _require_uuid(parent_block_id, "block_id")
    _require_positive(line_order, "line_order")
    return _uuid5(f"line:{parent_block_id}:{line_order}")


def span_id(parent_line_id: str, span_order: int) -> str:
    """Genera la identidad de un span tipográficamente homogéneo."""

    _require_uuid(parent_line_id, "line_id")
    _require_positive(span_order, "span_order")
    return _uuid5(f"span:{parent_line_id}:{span_order}")


def asset_id(asset_sha256: str) -> str:
    """Construye la identidad de contenido de un recurso binario."""

    _require_sha256(asset_sha256, "asset_sha256")
    return f"sha256:{asset_sha256}"


def asset_occurrence_id(
    parent_page_id: str,
    referenced_asset_id: str,
    occurrence_order: int,
) -> str:
    """Genera la identidad de una aparición concreta de un recurso."""

    _require_uuid(parent_page_id, "page_id")
    if not _ASSET_ID_PATTERN.fullmatch(referenced_asset_id):
        raise ValueError("asset_id must use the form 'sha256:<64 lowercase hex>'")
    _require_positive(occurrence_order, "occurrence_order")
    return _uuid5(
        f"asset-occurrence:{parent_page_id}:{referenced_asset_id}:{occurrence_order}"
    )


def _uuid5(suffix: str) -> str:
    """Aplica el namespace y prefijo canónicos del proyecto."""

    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{_NAME_PREFIX}:{suffix}"))


def _require_sha256(value: str, field_name: str) -> None:
    if not _SHA256_PATTERN.fullmatch(value):
        raise ValueError(f"{field_name} must contain 64 lowercase hexadecimal characters")


def _require_uuid(value: str, field_name: str) -> None:
    try:
        parsed = uuid.UUID(value)
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a valid UUID") from exc
    if parsed.version != 5:
        raise ValueError(f"{field_name} must be a UUID v5")


def _require_positive(value: int, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{field_name} must be an integer greater than or equal to 1")
