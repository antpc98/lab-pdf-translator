"""Carga y validación de la configuración base del proyecto.

Bitácora:
    2026-08-30 - Cargador inicial seguro para settings y glossary.

El cargador falla pronto: ningún documento debe procesarse con rutas ambiguas,
versiones de contrato incompatibles o campos desconocidos.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml


class ConfigurationError(ValueError):
    """Indica una configuración insegura, incompleta o incoherente."""


@dataclass(frozen=True, slots=True)
class LoadedConfiguration:
    """Configuración validada junto a la raíz que da sentido a sus rutas."""

    project_root: Path
    settings: dict[str, Any]
    glossary: dict[str, Any]

    def resolve_path(self, dotted_key: str) -> Path:
        """Resuelve una ruta configurada como ``paths.input_dir`` de forma segura."""

        section, key = dotted_key.split(".", maxsplit=1)
        value = self.settings[section][key]
        return _resolve_within_root(self.project_root, value, dotted_key)


def load_configuration(
    project_root: str | Path,
    *,
    local_settings_path: str | Path | None = None,
) -> LoadedConfiguration:
    """Carga configuración base, override local opcional y glosario."""

    root = Path(project_root).resolve()
    settings = _load_yaml_mapping(root / "config" / "settings.yaml")
    if local_settings_path is not None:
        local = _load_yaml_mapping(Path(local_settings_path))
        settings = _deep_merge(settings, local)

    glossary_path = _resolve_within_root(
        root,
        settings.get("translation", {}).get("glossary_path", ""),
        "translation.glossary_path",
    )
    glossary = _load_yaml_mapping(glossary_path)
    _validate_settings(root, settings)
    _validate_glossary(settings, glossary)
    return LoadedConfiguration(root, settings, glossary)


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as stream:
            value = yaml.safe_load(stream)
    except FileNotFoundError as exc:
        raise ConfigurationError(f"Configuration file not found: {path}") from exc
    except yaml.YAMLError as exc:
        raise ConfigurationError(f"Invalid YAML in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ConfigurationError(f"Configuration root must be a mapping: {path}")
    return value


def _validate_settings(root: Path, settings: Mapping[str, Any]) -> None:
    expected_sections = {
        "project",
        "contract",
        "paths",
        "pipeline",
        "extraction",
        "validation",
        "translation",
        "rendering",
        "logging",
    }
    _require_exact_keys(settings, expected_sections, "settings")

    pipeline = _require_mapping(settings, "pipeline")
    max_pages = pipeline.get("max_pages")
    if isinstance(max_pages, bool) or not isinstance(max_pages, int) or not 1 <= max_pages <= 1000:
        raise ConfigurationError("pipeline.max_pages must be an integer between 1 and 1000")
    batch_size = pipeline.get("batch_size")
    if isinstance(batch_size, bool) or not isinstance(batch_size, int) or batch_size < 1:
        raise ConfigurationError("pipeline.batch_size must be an integer greater than zero")
    for key in ("source_language", "target_language"):
        if not isinstance(pipeline.get(key), str) or not pipeline[key].strip():
            raise ConfigurationError(f"pipeline.{key} must be a non-empty language code")

    extraction = _require_mapping(settings, "extraction")
    if extraction.get("coordinate_precision") != 4:
        raise ConfigurationError("extraction.coordinate_precision must equal contract precision 4")
    pages = extraction.get("page_selection")
    if not isinstance(pages, list) or any(
        isinstance(page, bool) or not isinstance(page, int) or page < 1 for page in pages
    ):
        raise ConfigurationError("extraction.page_selection must contain positive page numbers")
    if len(pages) != len(set(pages)):
        raise ConfigurationError("extraction.page_selection must not contain duplicates")

    contract = _require_mapping(settings, "contract")
    schema_path = _resolve_within_root(root, contract.get("schema_path", ""), "contract.schema_path")
    if not schema_path.is_file():
        raise ConfigurationError(f"contract.schema_path does not exist: {schema_path}")
    if contract.get("schema_version") != "1.0.0" or contract.get("id_scheme_version") != 1:
        raise ConfigurationError("contract versions must match schema_version 1.0.0 and id_scheme_version 1")

    paths = _require_mapping(settings, "paths")
    resolved = {
        key: _resolve_within_root(root, value, f"paths.{key}")
        for key, value in paths.items()
    }
    if resolved.get("input_dir") in {path for key, path in resolved.items() if key != "input_dir"}:
        raise ConfigurationError("paths.input_dir must not be reused as an output directory")


def _validate_glossary(settings: Mapping[str, Any], glossary: Mapping[str, Any]) -> None:
    _require_exact_keys(
        glossary,
        {"version", "source_language", "target_language", "case_sensitive", "terms"},
        "glossary",
    )
    pipeline = _require_mapping(settings, "pipeline")
    if glossary.get("source_language") != pipeline.get("source_language"):
        raise ConfigurationError("glossary.source_language must match pipeline.source_language")
    if glossary.get("target_language") != pipeline.get("target_language"):
        raise ConfigurationError("glossary.target_language must match pipeline.target_language")
    if not isinstance(glossary.get("terms"), list):
        raise ConfigurationError("glossary.terms must be a list")


def _resolve_within_root(root: Path, value: Any, field_name: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError(f"{field_name} must be a non-empty relative path")
    candidate_value = Path(value)
    if candidate_value.is_absolute():
        raise ConfigurationError(f"{field_name} must be relative to the project root")
    candidate = (root / candidate_value).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ConfigurationError(f"{field_name} escapes the project root") from exc
    return candidate


def _require_mapping(settings: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = settings.get(key)
    if not isinstance(value, Mapping):
        raise ConfigurationError(f"{key} must be a mapping")
    return value


def _require_exact_keys(value: Mapping[str, Any], expected: set[str], path: str) -> None:
    actual = set(value)
    missing, unknown = expected - actual, actual - expected
    if missing:
        raise ConfigurationError(f"{path} is missing fields: {sorted(missing)}")
    if unknown:
        raise ConfigurationError(f"{path} contains unknown fields: {sorted(unknown)}")


def _deep_merge(base: Mapping[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    merged = deepcopy(dict(base))
    for key, value in override.items():
        if isinstance(value, Mapping) and isinstance(merged.get(key), Mapping):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged
