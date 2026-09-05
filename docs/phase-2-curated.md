# Fase 2: perfil documental y capa Curated

## Estado

Revision 2 está en `READY_FOR_HUMAN_REVIEW`. La capa es determinista, está validada y no contiene traducciones. El cierre de Fase 2 requiere revisar las muestras y riesgos residuales publicados en `exports/phase-2-revision-2-production/`.

## Flujo en dos pasadas

1. `build_document_profile` analiza únicamente RAW y produce familias tipográficas, geométricas, de navegación, etiquetas estructurales y señales técnicas.
2. `normalize` aplica ese perfil para crear unidades lógicas y añade clasificación semántica, rol documental, familia de clasificación, confianza, procedencia y política de traducción/protección.

El perfil se incorpora a `document.json` y también se publica en `document-profile.json`. Ambos se validan antes de sustituir el Curated publicado; RAW se comprueba por SHA-256 antes y después del proceso.

## Contrato semántico

Cada unidad declara:

- `semantic_type`: naturaleza semántica amplia, por ejemplo `body_text`, `navigation`, `code` o `technical`.
- `document_role`: función concreta, por ejemplo `paragraph`, `toc_entry`, `index_entry`, `page_number`, `code_block` o `technical_value`.
- `classification_family`: familia de evidencia que produjo la decisión.
- `classification_signals`, `confidence` y `reading_order_confidence`: evidencia y certeza auditables.
- `source`: páginas, bloques, líneas y spans RAW de procedencia.

Una entrada de TOC o índice conserva por separado `label`, `page_reference` y `page_reference_source_span_ids`. `page_reference` nunca se interpreta como número físico ni como `page_number`.

Los bloques de código son no traducibles y su texto debe ser exactamente la unión de `lines` con saltos de línea. Un `technical_value` también es no traducible y todos sus segmentos están protegidos. En prosa mixta, la unidad puede traducirse, pero sus tokens técnicos quedan como segmentos protegidos.

## Contrato de consumo para Fase 3

Fase 3 debe consumir `f3-translation-stream.csv` sin reinterpretar el PDF:

- `TRANSLATE`: traducir texto conservando literalmente los segmentos protegidos.
- `SKIP`: omitir contenido no traducible sin segmentos protegidos.
- `PROTECT_ONLY`: copiar literalmente la unidad protegida.
- `HUMAN_REVIEW`: excluir de traducción automática hasta que una persona resuelva el caso.

Las advertencias `AMBIGUOUS_READING_ORDER` deben conservarse como riesgo explícito. Ningún consumidor debe reclasificar silenciosamente `unknown`, código, referencias de navegación o paginación.

## Validación

`scripts/validate_phase2.py` valida esquema, perfil, igualdad del perfil embebido, procedencia, protección, integridad de código, separación de referencias y regresiones técnicas conocidas. `scripts/quality_gate.py` integra estas verificaciones con tests, cobertura, contrato RAW y assets.
