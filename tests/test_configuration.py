"""Pruebas unitarias de carga, precedencia y seguridad de configuración.

Bitácora: 2026-08-30 - Configuración base y overrides locales.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from lab_pdf_translator.config import ConfigurationError, load_configuration


def test_base_configuration_loads_and_resolves_paths(project_root: Path) -> None:
    configuration = load_configuration(project_root)
    assert configuration.settings["contract"]["schema_version"] == "1.0.0"
    assert configuration.glossary["target_language"] == "es"
    assert configuration.resolve_path("paths.input_dir") == project_root / "input"


def test_local_override_is_deep_merged(project_root: Path, tmp_path: Path) -> None:
    local = tmp_path / "settings.local.yaml"
    local.write_text("logging:\n  level: DEBUG\n", encoding="utf-8")
    configuration = load_configuration(project_root, local_settings_path=local)
    assert configuration.settings["logging"]["level"] == "DEBUG"
    assert configuration.settings["logging"]["console"] is True


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ("pipeline:\n  max_pages: 1001\n", "between 1 and 1000"),
        ("pipeline:\n  batch_size: 0\n", "greater than zero"),
        ("extraction:\n  coordinate_precision: 3\n", "precision 4"),
        ("extraction:\n  page_selection: [1, 1]\n", "must not contain duplicates"),
        ("paths:\n  raw_data_dir: input\n", "must not be reused"),
        ("contract:\n  schema_version: 2.0.0\n", "must match"),
        ("unexpected_section:\n  enabled: true\n", "unknown fields"),
    ],
)
def test_invalid_local_overrides_fail_before_processing(
    project_root: Path,
    tmp_path: Path,
    override: str,
    message: str,
) -> None:
    local = tmp_path / "settings.local.yaml"
    local.write_text(override, encoding="utf-8")
    with pytest.raises(ConfigurationError, match=message):
        load_configuration(project_root, local_settings_path=local)


def test_invalid_yaml_is_reported_with_file_context(
    project_root: Path, tmp_path: Path
) -> None:
    local = tmp_path / "settings.local.yaml"
    local.write_text("pipeline: [unterminated", encoding="utf-8")
    with pytest.raises(ConfigurationError, match="Invalid YAML"):
        load_configuration(project_root, local_settings_path=local)


def test_absolute_or_escaping_paths_are_rejected(project_root: Path, tmp_path: Path) -> None:
    absolute = tmp_path / "settings.absolute.yaml"
    absolute.write_text(f"paths:\n  raw_data_dir: '{tmp_path.as_posix()}'\n", encoding="utf-8")
    with pytest.raises(ConfigurationError, match="relative"):
        load_configuration(project_root, local_settings_path=absolute)

    escaping = tmp_path / "settings.escape.yaml"
    escaping.write_text("paths:\n  raw_data_dir: ../outside\n", encoding="utf-8")
    with pytest.raises(ConfigurationError, match="escapes"):
        load_configuration(project_root, local_settings_path=escaping)


def test_missing_or_non_mapping_configuration_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="not found"):
        load_configuration(tmp_path)

    local = tmp_path / "not-a-mapping.yaml"
    local.write_text("[]\n", encoding="utf-8")
    with pytest.raises(ConfigurationError, match="root must be a mapping"):
        load_configuration(Path(__file__).resolve().parents[1], local_settings_path=local)


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ("pipeline:\n  source_language: ''\n", "non-empty language"),
        ("extraction:\n  page_selection: [0]\n", "positive page numbers"),
        ("contract:\n  schema_path: schemas/missing.json\n", "does not exist"),
    ],
)
def test_additional_contract_guards(
    project_root: Path,
    tmp_path: Path,
    override: str,
    message: str,
) -> None:
    local = tmp_path / "settings.local.yaml"
    local.write_text(override, encoding="utf-8")
    with pytest.raises(ConfigurationError, match=message):
        load_configuration(project_root, local_settings_path=local)


def test_glossary_languages_must_match_pipeline(project_root: Path, tmp_path: Path) -> None:
    local = tmp_path / "settings.local.yaml"
    local.write_text(
        "translation:\n  glossary_path: tests/fixtures/glossary-mismatch.yaml\n",
        encoding="utf-8",
    )
    with pytest.raises(ConfigurationError, match="source_language must match"):
        load_configuration(project_root, local_settings_path=local)
