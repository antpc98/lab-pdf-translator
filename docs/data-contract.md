# Contrato de datos de la capa raw

> Bitácora: 30/08/2026 — contrato revisado al incorporar validación estructural, semántica y pruebas deterministas.

## Estado y alcance

- Versión del contrato: `1.0.0`.
- Versión del esquema de identificación: `1`.
- Especificación: JSON Schema Draft 2020-12.
- Esquema canónico: `schemas/document.schema.json`.
- Alcance: extracción de documentos PDF en la capa inmutable `raw`.

Las capas `curated` y `translated` tendrán contratos propios. Podrán añadir contenido normalizado o traducido, pero deberán conservar referencias explícitas a los IDs de la capa `raw`.

## Entidades

### Document

Representa una versión binaria exacta de un archivo de entrada. Contiene:

- Identidad y versión del contrato.
- Metadatos del archivo de origen.
- Procedencia y estado de la extracción.
- Páginas físicas en orden.
- Registro único de recursos binarios.
- Advertencias que afecten al documento completo.

### Page

Representa una página física del PDF. Conserva número físico, etiqueta impresa opcional, dimensiones, rotación, estado, bloques y apariciones de recursos.

Una página vacía es válida y se representa mediante `blocks: []`. Una página que no pudo extraerse debe permanecer en el dataset con `status: "failed"` y al menos una advertencia.

### Block

Unidad estructural detectada en una página. El catálogo inicial es:

- `title`
- `heading`
- `paragraph`
- `list_item`
- `table`
- `code`
- `image`
- `caption`
- `header`
- `footer`
- `page_number`
- `unknown`

Una clasificación incierta usa `unknown`; nunca provoca la eliminación silenciosa del bloque.

### Line y Span

Una línea agrupa fragmentos de texto relacionados geométricamente. Un `span` es el fragmento mínimo con propiedades tipográficas homogéneas.

`span.text` conserva exactamente la secuencia Unicode entregada por el extractor. En la capa `raw` no se aplican normalización Unicode, corrección de ligaduras, unión de palabras, limpieza de espacios ni modificación de saltos. Esas operaciones pertenecen a `curated`.

Los fragmentos invisibles o rotados se conservan y se describen mediante sus propiedades. Un fragmento puede contener una cadena vacía si el extractor ha identificado su geometría o estilo.

### Asset y AssetOccurrence

`asset` representa un binario único identificado por su contenido. `asset_occurrence` representa una aparición concreta en una página y conserva posición, transformación y orden.

El mismo recurso puede aparecer varias veces. Esas apariciones comparten `asset_id`, pero tienen distintos `asset_occurrence_id`. Un bloque de tipo `image` puede referenciar una o más apariciones mediante `asset_occurrence_ids`.

## Identificadores

Los hashes se serializan en hexadecimal minúsculo. Los UUID usan UUID v5, el namespace estándar `NAMESPACE_URL` y nombres UTF-8.

```text
source_sha256 = SHA-256(bytes exactos del archivo)

document_id = UUIDv5(
  NAMESPACE_URL,
  "lab-pdf-translator:document:sha256:{source_sha256}"
)

page_id = UUIDv5(
  NAMESPACE_URL,
  "lab-pdf-translator:page:{document_id}:{page_number}"
)

block_id = UUIDv5(
  NAMESPACE_URL,
  "lab-pdf-translator:block:{page_id}:{block_order}"
)

line_id = UUIDv5(
  NAMESPACE_URL,
  "lab-pdf-translator:line:{block_id}:{line_order}"
)

span_id = UUIDv5(
  NAMESPACE_URL,
  "lab-pdf-translator:span:{line_id}:{span_order}"
)

asset_id = "sha256:{asset_sha256}"

asset_occurrence_id = UUIDv5(
  NAMESPACE_URL,
  "lab-pdf-translator:asset-occurrence:{page_id}:{asset_id}:{occurrence_order}"
)
```

El nombre y la ubicación del archivo no participan en `document_id`. Si cambia un byte, el archivo se considera una versión documental diferente. La fecha de extracción tampoco participa en ningún ID.

## Orden determinista

Los contadores empiezan en `1`.

La primera versión utiliza un orden geométrico estable. Antes de comparar, las coordenadas se redondean a cuatro decimales.

```text
block_order = sort(y0, x0, y1, x1, source_index)
line_order  = sort(y0, x0, y1, x1, source_index) dentro del bloque
span_order  = sort(y0, x0, y1, x1, source_index) dentro de la línea
occurrence_order = sort(y0, x0, y1, x1, asset_id, source_index) en la página
```

`source_index` es la posición original entregada por el extractor y actúa como último desempate. El orden geométrico no intenta reconstruir semánticamente documentos multicolumna; la reconstrucción semántica pertenece a `curated`.

Procesar los mismos bytes con las mismas versiones de contrato, esquema de IDs y extractor debe generar los mismos IDs. Un cambio del algoritmo que pueda alterar IDs obliga a incrementar `id_scheme_version`.

## Geometría

- Unidad: punto PDF (`1/72` de pulgada).
- Origen: esquina superior izquierda.
- Eje X: crece hacia la derecha.
- Eje Y: crece hacia abajo.
- Caja: `[x0, y0, x1, y1]`.
- Precisión canónica: máximo cuatro decimales.
- Límites: `0 <= x0 <= x1 <= page.width` y `0 <= y0 <= y1 <= page.height`.

Las dimensiones representan el área visible normalizada de la página (`CropBox`). `media_box` conserva, cuando esté disponible, la caja física original. Las coordenadas se almacenan después de aplicar la rotación declarada por el PDF; `rotation` conserva el valor original normalizado a `0`, `90`, `180` o `270`.

JSON Schema valida la forma y restricciones locales. Las relaciones entre dimensiones y coordenadas requieren validaciones semánticas adicionales.

## Procedencia y estados

La extracción registra:

- Nombre original, MIME, tamaño y SHA-256.
- Nombre y versión del extractor.
- Fecha UTC en formato RFC 3339.
- Estado `complete`, `partial` o `failed`.
- Advertencias estructuradas con código, mensaje, ámbito y referencia opcional.

Las advertencias no modifican IDs. Un documento parcial debe conservar todas las páginas conocidas y señalar expresamente las que fallaron. Un PDF protegido o ilegible puede producir un documento con estado `failed`, siempre que estén disponibles los metadatos mínimos de origen.

## Evolución del contrato

Se aplica versionado semántico:

- `PATCH`: aclaraciones o restricciones compatibles que no cambian datos válidos.
- `MINOR`: incorporación compatible de campos opcionales o nuevos valores previstos.
- `MAJOR`: eliminación, cambio de significado o modificación incompatible de campos.

Los datasets conservan `schema_version` e `id_scheme_version`. Los esquemas publicados no se sobrescriben de forma incompatible.

## Criterios de aceptación

La definición del contrato `raw` se considera terminada cuando:

1. Existe un JSON Schema Draft 2020-12 sintácticamente válido.
2. El esquema prohíbe propiedades desconocidas en las entidades del contrato.
3. Existe un ejemplo mínimo válido y otro representativo.
4. Existen casos inválidos para campos obligatorios y formatos de identidad.
5. Las reglas de identidad, orden, geometría, procedencia y versionado están documentadas.
6. Los JSON de ejemplo tienen sintaxis válida.

Los seis criterios están cubiertos. Además, `validation/schema.py` ejecuta los ejemplos contra el esquema, `validation/semantic.py` comprueba las reglas que exceden JSON Schema y las pruebas automatizadas verifican las propiedades deterministas de los identificadores.
