# Fase 2 — informe final aceptado

## Estado

F0 y F1 están terminadas. F2 está aceptada técnicamente y pendiente únicamente del commit/push de finalización. F3–F6 no se han iniciado.

## Alcance y arquitectura

F2 recibe el contrato RAW inmutable de F1 y ejecuta dos pasos deterministas: primero crea un `DocumentProfile` específico del documento desde tipografía, geometría, recurrencia, navegación y señales técnicas; después normaliza unidades lógicas Curated con `semantic_type`, `document_role`, `classification_family`, orden, procedencia y protección técnica.

El perfil se publica en `data/curated/document-profile.json` y se incorpora en `data/curated/document.json`. Ambos se generan exclusivamente desde `data/raw/document.json`.

## Invariantes aceptados

- RAW permanece inmutable y sus hashes se verifican antes y después de normalizar.
- Curated conserva procedencia de páginas, bloques, líneas y spans RAW.
- Las referencias de TOC/índice (`page_reference`) son distintas de los números físicos (`page_number`).
- Código y valores técnicos aislados no son traducibles; los segmentos técnicos inline permanecen protegidos.
- F3 deriva una única acción por unidad: `TRANSLATE`, `SKIP`, `PROTECT_ONLY` o `HUMAN_REVIEW`.
- Esquema, validación semántica, integridad de código y determinismo forman parte del Quality Gate.

## Resultado aceptado

La auditoría final encontró cero bloqueadores, cero riesgos altos y cero traducciones inseguras conocidas. El Quality Gate aprobó 68 pruebas con 92,61 % de cobertura. Las métricas y hashes exactos pertenecen a los artefactos locales generados de auditoría, no al historial Git.

## Contrato para F3

F3 opera solo sobre Curated: `unit_id`, `reading_order`, `text`, `semantic_type`, `document_role`, `classification_family`, `section_path`, `translatable`, `segments`, procedencia y señales de clasificación son suficientes para decidir, traducir y restaurar tokens protegidos sin reinterpretar el PDF.

## Deuda no bloqueante

- 242 unidades `HUMAN_REVIEW`, excluidas de traducción automática.
- 36 advertencias explícitas de orden de lectura, todas de severidad baja.
- 51 candidatos geométricos para muestreo futuro de orden de lectura.
- 117 posibles continuaciones entre páginas; ninguna clasificada como probable.
- Validación futura de generalización del perfil sobre más tipos de documento.

## Patch contractual para F3

El bloqueo de rangos protegidos no alineados con el texto Curated quedó resuelto mediante el contrato 2.1.0. Los segmentos protegidos llevan rangos `start`/`end` de índices Python sobre el texto canónico, con validación de límites, igualdad de substring, orden y ausencia de solapamientos. El enriquecimiento no altera unidades, orden, texto, clasificación, procedencia ni perfil documental.
