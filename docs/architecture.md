# Arquitectura

```text
PDF
 │
 ▼
F1 extraction ──► data/raw/document.json (inmutable)
 │                     │
 │                     ▼
 │              F2 DocumentProfile
 │                     │
 └────────────────────► F2 semantic normalization
                              │
                              ▼
                    data/curated/document.json
                              │
                              ▼
          TRANSLATE | SKIP | PROTECT_ONLY | HUMAN_REVIEW
```

## Módulos reales

| Módulo | Responsabilidad | Entrada | Salida | Fase |
|---|---|---|---|---|
| `extraction/service.py` | Descubrir y extraer PDF con IDs estables | PDF | RAW y assets | F1 |
| `models/identifiers.py` | IDs deterministas y hashes | contenido | IDs/hash | F1/F2 |
| `curation/profile.py` | Descubrir familias estructurales por documento | RAW | `DocumentProfile` | F2 |
| `curation/service.py` | Reconstrucción y normalización semántica | RAW + perfil | Curated | F2 |
| `validation/schema.py` | Validar JSON Schema | documento | incidencias | F0–F2 |
| `validation/semantic.py` | Validar invariantes RAW | RAW | incidencias | F1 |
| `validation/curated.py` | Validar invariantes Curated | Curated + RAW | incidencias | F2 |
| `scripts/validate_phase2.py` | Validar publicación Curated/Profile | artefactos | resultado fail-closed | F2 |
| `scripts/quality_gate.py` | Integrar contrato, pruebas y cobertura | repositorio | Quality Gate | F0–F2 |

## Datos canónicos locales

`data/raw/document.json` es el contrato inmutable de entrada validado. `data/curated/document.json` y `data/curated/document-profile.json` son salidas deterministas canónicas para el documento de validación. Por política del repositorio se ignoran: se regeneran desde el PDF/RAW y no se versionan como parte del código.

## Frontera de F3

F3 no necesita consultar PDF ni RAW para clasificar contenido. Debe preservar orden y contexto de sección, aplicar exactamente una acción por unidad y restaurar los segmentos protegidos de forma literal después de traducir el texto permitido.
