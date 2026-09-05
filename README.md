# Lab PDF Translator

Laboratorio para construir un flujo reproducible de extracción, gobierno, traducción y reconstrucción de documentos.

El sistema transformará cada documento de entrada en un conjunto de datos estructurado y trazable. Sobre ese dataset se aplicarán reglas de normalización y traducción y, finalmente, se generará un documento cómodo de leer.

> Estado actual (05/09/2026): **fase 1 completada**. La extracción RAW usa PyMuPDF, IDs deterministas, validación, publicación atómica y checkpoints de reanudación.

## Ejecutar la Fase 1

Coloque exactamente un PDF en `input/` y ejecute en PowerShell:

```powershell
.\run_lab.ps1
```

Si hay varios PDFs, seleccione uno sin ambigüedad:

```powershell
.\run_lab.ps1 -InputFile .\input\document.pdf
```

El resultado validado se publica en `data/raw/document.json`; las imágenes deduplicadas se guardan en `assets/images/`. Los checkpoints temporales están en `checkpoints/` y permiten continuar mediante `-Resume`; se eliminan automáticamente tras una ejecución satisfactoria. Los logs operacionales están en `logs/phase-1-extraction.log`.

Para aprobar todos los controles, incluido RAW, assets, tests y cobertura:

```powershell
.\.venv\Scripts\python.exe .\scripts\quality_gate.py
```

## Objetivos

- Convertir documentos en datasets estructurados sin perder la información necesaria para reconstruirlos.
- Normalizar y gobernar los datos antes de traducirlos.
- Traducir el contenido con precisión, coherencia terminológica y trazabilidad.
- Generar documentos finales legibles en PDF y, posteriormente, en Word (`.docx`).
- Permitir seleccionar los idiomas de origen y destino.
- Diseñar el flujo para documentos de entre 1 y 1000 páginas.

## Flujo del documento

```text
Documento de entrada
        │
        ▼
Extracción estructurada
        │
        ▼
Dataset raw (contenido original)
        │
        ▼
Normalización y gobierno
        │
        ▼
Dataset curated (contenido preparado)
        │
        ▼
Traducción y validación
        │
        ▼
Dataset translated
        │
        ▼
Renderizado y composición
        │
        ├── PDF
        └── DOCX
```

Cada capa debe poder generarse de manera independiente, validarse y reutilizarse sin tener que repetir todo el procesamiento.

## Alcance funcional

### Documentos de entrada

- PDF con texto digital.
- Documentos de entre 1 y 1000 páginas.
- Soporte futuro para PDF escaneado mediante OCR.
- Soporte futuro para otros formatos de entrada si el laboratorio lo requiere.

### Idiomas

- Selección explícita del idioma de origen.
- Detección automática del idioma de origen como opción futura.
- Selección del idioma de destino.
- Español como primer idioma de destino implementado.
- Arquitectura preparada para incorporar los principales idiomas internacionales.
- Compatibilidad progresiva con alfabetos y sistemas de composición especiales, como árabe, hebreo, chino, japonés y coreano.

### Dataset y gobierno

El dataset debe conservar tanto el contenido como su relación con el documento original. Como mínimo incluirá:

- Documento, página y bloque de procedencia.
- Identificadores únicos y estables.
- Texto original y texto normalizado.
- Orden de lectura.
- Tipo de bloque: título, párrafo, lista, tabla, código, pie de página u otro.
- Coordenadas de posición (`bbox`).
- Familia, tamaño y estilo de fuente.
- Referencias a imágenes y otros recursos.
- Idioma de origen y destino.
- Estado y versión de la traducción.
- Reglas de glosario aplicadas.
- Errores, advertencias y resultados de validación.
- Trazabilidad entre el bloque original y el traducido.

La capa `raw` será inmutable: representará el contenido extraído sin correcciones ni traducciones. Las transformaciones se guardarán en capas posteriores.

### Contrato de datos inicial

El contrato de datos comienza en la versión `1.0.0`, utiliza **JSON Schema Draft 2020-12** y se limita inicialmente a la capa inmutable `raw`. Las capas `curated` y `translated` tendrán contratos propios y conservarán referencias explícitas a los IDs de origen.

El contrato formal está disponible en `schemas/document.schema.json` y su explicación ampliada en `docs/data-contract.md`. Los datasets declaran `schema_version` e `id_scheme_version`.

#### Jerarquía del documento

```text
document
├── pages[]
│   ├── blocks[]
│   │   ├── lines[]
│   │   │   └── spans[]
│   │   └── asset_occurrence_ids[]
│   └── asset_occurrences[]
└── assets[]
```

- `document` contiene la identidad del archivo, sus metadatos y la colección ordenada de páginas.
- `page` representa una página física del PDF.
- `block` representa una unidad estructural, como un título, párrafo, lista, tabla, código, imagen, encabezado o pie.
- `line` conserva las líneas detectadas dentro de un bloque.
- `span` conserva el fragmento mínimo de texto con propiedades tipográficas homogéneas.
- `asset` representa un recurso binario único, identificado por su contenido.
- `asset_occurrence` representa una aparición concreta del recurso y conserva página, posición, transformación y orden.

Los campos obligatorios, opcionales, tipos, formatos, enumeraciones y valores permitidos se especifican en `schemas/document.schema.json`. Las propiedades desconocidas no están permitidas en las entidades del contrato.

El catálogo inicial de `block_type` incluye `title`, `heading`, `paragraph`, `list_item`, `table`, `code`, `image`, `caption`, `header`, `footer`, `page_number` y `unknown`. Una clasificación incierta usa `unknown`; nunca elimina silenciosamente el bloque.

El texto de cada `span` conserva la secuencia Unicode entregada por el extractor. La capa `raw` no corrige ligaduras, espacios, guiones, saltos ni caracteres; cualquier normalización pertenece a `curated`.

#### Sistema de coordenadas

- Las coordenadas se normalizarán a puntos PDF; un punto equivale a `1/72` de pulgada.
- El origen estará en la esquina superior izquierda de la página.
- El eje X crecerá hacia la derecha y el eje Y hacia abajo.
- Una caja se representará como `bbox: [x0, y0, x1, y1]`.
- Deberá cumplirse `x0 <= x1` y `y0 <= y1`.
- Cada página conservará su anchura, altura y rotación para poder interpretar correctamente sus coordenadas.
- Los números se almacenarán con un máximo de cuatro decimales.
- Las dimensiones visibles se basarán en `CropBox`; `media_box` conservará la caja física original cuando esté disponible.
- Las coordenadas se almacenarán después de aplicar la rotación de página, que se conservará como `0`, `90`, `180` o `270`.
- Las validaciones semánticas comprobarán que las cajas estén dentro de los límites de su página.

#### Numeración de páginas

- `page_number` identificará la posición física de la página dentro del PDF y comenzará en `1`.
- `printed_page_label` almacenará, cuando pueda detectarse, la numeración visible impresa en el documento.
- La identidad y el orden del dataset siempre utilizarán `page_number`; nunca dependerán de `printed_page_label`.

#### Identificadores deterministas

Todos los identificadores se calcularán a partir de valores canónicos. Para los UUID se utilizará UUID v5 con el namespace estándar `NAMESPACE_URL` y una cadena de nombre UTF-8 con los formatos siguientes:

```text
source_sha256 = SHA-256 de los bytes exactos del archivo de entrada

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

Reglas asociadas:

- `page_number`, `block_order`, `line_order` y `span_order` comenzarán en `1`.
- `occurrence_order` también comenzará en `1`.
- Los hashes se serializarán en hexadecimal minúsculo.
- Bloques, líneas y spans se ordenarán por `(y0, x0, y1, x1, source_index)` después de redondear las coordenadas a cuatro decimales.
- Las apariciones se ordenarán por `(y0, x0, y1, x1, asset_id, source_index)`.
- `source_index` conservará la posición entregada por el extractor y actuará como último desempate.
- Este orden geométrico no reconstruirá semánticamente documentos multicolumna; esa tarea pertenecerá a `curated`.
- Procesar de nuevo el mismo archivo con la misma versión del contrato y del extractor producirá los mismos IDs.
- El nombre o la ubicación del archivo no formarán parte de su identidad.
- Si cambia cualquier byte del archivo de entrada, cambiarán `source_sha256` y `document_id`; el archivo será tratado como una nueva versión documental.
- Recursos binarios idénticos compartirán `asset_id`, aunque aparezcan varias veces.
- Los IDs de las capas `curated` y `translated` conservarán referencias explícitas a los IDs de origen y no reemplazarán la identidad de los elementos `raw`.
- Cualquier cambio de algoritmo que pueda alterar IDs incrementará `id_scheme_version`.

#### Procedencia, errores y evolución

- La procedencia registra nombre original, MIME, tamaño, SHA-256, extractor, versión, fecha UTC y estado.
- La fecha de extracción es informativa y no participa en los IDs.
- Los estados posibles son `complete`, `partial` y `failed`.
- Las páginas vacías se conservan con `blocks: []`.
- Las páginas o documentos ilegibles, protegidos o parcialmente extraídos se conservan con su estado y advertencias; no desaparecen silenciosamente.
- El contrato sigue versionado semántico: `PATCH` para cambios compatibles, `MINOR` para adiciones opcionales compatibles y `MAJOR` para cambios incompatibles.

#### Artefactos del contrato

- `schemas/document.schema.json`: contrato formal versionado.
- `schemas/examples/document.minimal.valid.json`: documento mínimo válido.
- `schemas/examples/document.representative.valid.json`: bloques, texto, tipografía y recursos.
- `schemas/examples/document.missing-id.invalid.json`: ausencia de un campo obligatorio.
- `schemas/examples/document.bad-identity.invalid.json`: formatos y valores no permitidos.
- `docs/data-contract.md`: decisiones completas de identidad, orden, geometría, errores y evolución.

La definición documental y su implementación de referencia están cerradas. Los ejemplos se validan automáticamente contra el esquema; las comprobaciones semánticas verifican geometría, relaciones, orden e IDs, y las pruebas confirman la estabilidad determinista.

### Traducción

- Traducción por bloques con preservación del contexto del documento.
- Uso de glosarios para términos técnicos, nombres propios y expresiones que no deban traducirse.
- Coherencia terminológica entre páginas y capítulos.
- Protección de código, direcciones, cifras, fórmulas y otros elementos sensibles.
- Registro del proveedor, modelo o motor utilizado y de la versión del proceso.
- Posibilidad de reintentar únicamente los bloques fallidos.
- Validaciones automáticas antes de aceptar el dataset traducido.

### Visualización y salida

La primera salida será un PDF cómodo de leer.

- Conservar la familia, el estilo y el tamaño de letra siempre que el espacio disponible lo permita.
- Evitar texto cortado, superpuesto o fuera de página.
- Mantener imágenes, listas, bloques de código y estructura básica.
- Permitir redistribuir el texto cuando la traducción ocupe más espacio que el original.
- Incorporar una portada estándar configurable.
- Incorporar un pie de página con numeración correcta.
- Generar posteriormente una versión Word (`.docx`) editable para ajustes manuales e incorporación de imágenes.

La fidelidad visual exacta no es el objetivo de la primera versión. Se priorizarán la integridad del contenido y la legibilidad.

## Requisitos no funcionales

- **Reproducibilidad:** la misma entrada y configuración deben producir resultados equivalentes.
- **Idempotencia:** el flujo puede ejecutarse varias veces sin corromper ni duplicar datos.
- **Trazabilidad:** cada elemento traducido puede relacionarse con su origen.
- **Procesamiento incremental:** una ejecución interrumpida puede continuar desde el último punto válido.
- **Escalabilidad:** el documento se procesa por páginas o lotes para admitir hasta 1000 páginas.
- **Validación:** cada fase comprueba su salida antes de habilitar la siguiente.
- **Observabilidad:** se registran tiempos, errores, advertencias y métricas básicas.
- **Configurabilidad:** idiomas, glosarios, motor de traducción y opciones de salida no estarán fijados en el código.

## Entorno y librerías seleccionadas

El entorno objetivo inicial es **CPython 3.14.7**. Las dependencias directas están fijadas en `requirements.txt` y su elección, alcance, licencia y política de actualización se documentan en `docs/technology-stack.md`.

| Responsabilidad | Librería |
|---|---|
| Extracción y análisis PDF | PyMuPDF 1.28.2 |
| Validación JSON Schema | jsonschema 4.26.0 |
| Generación de PDF | ReportLab 5.0.1 |
| Generación de Word | python-docx-ng 2.1.0 |
| Procesamiento de imágenes | Pillow 12.3.0 |
| Configuración YAML | PyYAML 6.0.3 |

OCR, traducción y detección automática de idioma quedan fuera de esta selección y se decidirán en sus respectivas fases. Antes de distribuir el proyecto como producto cerrado deberá revisarse la licencia AGPL/comercial de PyMuPDF.

## Documentación detallada

- [`docs/project-structure.md`](docs/project-structure.md): recorrido completo del documento, función de cada carpeta, límites entre módulos y reglas de versionado.
- [`docs/configuration.md`](docs/configuration.md): explicación desde los fundamentos de YAML hasta cada opción, su validación y su efecto sobre la reproducibilidad.
- [`docs/data-contract.md`](docs/data-contract.md): contrato semántico de la capa `raw`, geometría, IDs y evolución.
- [`docs/technology-stack.md`](docs/technology-stack.md): librerías seleccionadas, responsabilidades, versiones, compatibilidad y licencias.
- [`docs/testing-and-validation.md`](docs/testing-and-validation.md): estrategia de pruebas, muestras, comandos, resultados esperados y diagnóstico de fallos.
- [`docs/automated-quality-gate.md`](docs/automated-quality-gate.md): barrera única, bootstrap de entorno, códigos de salida y futura integración continua.
- [`docs/test-document-governance.md`](docs/test-document-governance.md): separación entre muestras privadas y publicables, licencias, atribución y migración.
- [`docs/phase-1-extraction-plan.md`](docs/phase-1-extraction-plan.md): subtareas, arquitectura, reanudación, evidencias y Definition of Done de la extracción `raw`.

## Arquitectura del proyecto

```text
lab-pdf-translator/
├── input/                 # Documentos de entrada
├── data/
│   ├── raw/               # Extracción inmutable
│   ├── curated/           # Datos normalizados y gobernados
│   └── translated/        # Datos traducidos y validados
├── assets/
│   └── images/            # Imágenes y recursos extraídos
├── config/
│   ├── glossary.yaml      # Glosario y términos protegidos
│   └── settings.yaml      # Configuración del flujo
├── schemas/
│   ├── document.schema.json
│   └── examples/           # Ejemplos válidos e inválidos
├── docs/
│   ├── data-contract.md    # Contrato de datos ampliado
│   ├── technology-stack.md # Selección y uso de librerías
│   ├── project-structure.md# Guía del flujo y de cada carpeta
│   ├── configuration.md    # Referencia completa de configuración
│   ├── testing-and-validation.md # Pruebas y validación automática
│   ├── automated-quality-gate.md # Puerta única de aprobación
│   ├── test-document-governance.md # Uso privado y publicación
│   └── phase-1-extraction-plan.md # Plan y Done de extracción raw
├── src/
│   └── lab_pdf_translator/
│       ├── models/         # Entidades e identificadores deterministas
│       ├── extraction/     # Lectura y extracción de documentos
│       ├── processing/     # Limpieza, clasificación y normalización
│       ├── translation/    # Motores y reglas de traducción
│       ├── validation/     # Controles de calidad
│       └── rendering/      # Generación de PDF y DOCX
├── scripts/               # Puntos de entrada del flujo
├── output/                # Documentos generados
├── logs/                  # Evidencia operacional local
├── tests/                 # Pruebas automáticas y muestras
├── requirements.txt
└── README.md
```

La estructura mínima ya está creada. Los paquetes delimitan responsabilidades, pero todavía no implementan el procesamiento; se completarán progresivamente durante las fases de desarrollo. Los datasets, imágenes, documentos finales, logs y el entorno `.venv` están excluidos de Git mediante `.gitignore`.

## Fases de desarrollo

### Fase 0 — Definición y entorno

- [x] Definir el esquema de datos de la capa `raw` y sus reglas de identificación.
- [x] Formalizar el contrato mediante JSON Schema Draft 2020-12.
- [x] Crear documentación y ejemplos válidos e inválidos del contrato.
- [x] Elegir y documentar las librerías de extracción, validación y renderizado.
- [x] Crear y documentar la estructura mínima del proyecto y su configuración base.
- [x] Preparar pruebas unitarias, validaciones automáticas y muestras representativas.

**Resultado:** contrato de datos versionado, proyecto ejecutable y controles automáticos reproducibles en local. La fase 0 queda cerrada el 30/08/2026 con 58 pruebas superadas, una cobertura de código del 90,98 % y una barrera integral de calidad.

### Ejecutar las comprobaciones de la fase 0

En Windows, el lanzador crea y activa el entorno cuando sea necesario, instala las dependencias y ejecuta todos los controles:

```powershell
.\scripts\run_quality_gate.cmd
```

El proceso debe mostrar dependencias, pruebas y aceptación como `[PASS]`, finalizar con `RESULT: PASS` y devolver el código `0`. La operación se explica en [`docs/automated-quality-gate.md`](docs/automated-quality-gate.md).

### Fase 1 — Extracción estructurada

Convertir un PDF digital compatible en una representación `raw` completa, inmutable, trazable y reproducible, sin normalizar, corregir o traducir su contenido. El plan completo y los criterios del review están en [`docs/phase-1-extraction-plan.md`](docs/phase-1-extraction-plan.md).

- [ ] Definir el contrato de ejecución, la CLI, los códigos de salida y la validación segura de entradas.
- [ ] Implementar modelos y serialización JSON ajustados al contrato `raw` 1.0.0.
- [ ] Inspeccionar documento, metadatos, páginas físicas, cajas, rotación, hash y procedencia.
- [ ] Extraer bloques, líneas, spans, texto, geometría, fuentes, tamaños y estilos sin normalización.
- [ ] Aplicar orden técnico determinista conservando la trazabilidad del motor.
- [ ] Clasificar conservadoramente títulos, párrafos, listas, código, imágenes, encabezados y pies.
- [ ] Extraer, identificar, deduplicar y guardar imágenes junto con todas sus apariciones.
- [ ] Generar IDs estables reutilizando exclusivamente el esquema de identificación versionado.
- [ ] Implementar escritura temporal y publicación atómica de `document.json` y assets.
- [ ] Implementar checkpoints compatibles y reanudación sin pérdidas ni duplicados.
- [ ] Añadir logs, métricas, warnings y estados `complete`, `partial` y `failed`.
- [ ] Preparar pruebas unitarias, contrato, integración, repetición, interrupción y reanudación.
- [ ] Validar automáticamente y revisar visualmente las páginas representativas.
- [ ] Actualizar documentación, barrera de calidad y evidencias del review.

**Resultado:** `data/raw/document.json` y recursos asociados.

**Validación inicial:** páginas físicas 19, 22 y 31, más portada, página gráfica, definición, lista y contraportada declaradas en el manifiesto. El dataset debe superar JSON Schema, validación semántica, estabilidad de IDs, reanudación simulada, cobertura mínima del 90 % y la barrera automática completa.

**Criterio de Done:** ninguna página perdida, texto `raw` sin alteraciones, geometría y assets trazables, salida atómica válida, repetición estable, reanudación demostrada, documentación completa y ausencia de defectos críticos o altos.

### Fase 2 — Normalización y gobierno

- Limpiar artefactos de extracción sin alterar el significado.
- Reconstruir párrafos divididos entre líneas o páginas.
- Clasificar los bloques del documento.
- Detectar encabezados y pies repetidos.
- Proteger código, cifras, fórmulas, enlaces y términos especiales.
- Aplicar y registrar reglas de calidad.
- Mantener la trazabilidad completa con la capa `raw`.

**Resultado:** `data/curated/blocks.jsonl` preparado para traducción.

### Fase 3 — Traducción al español

- Integrar el primer motor de traducción mediante una interfaz intercambiable.
- Aplicar glosarios y términos protegidos.
- Traducir por lotes conservando contexto.
- Registrar el estado de cada bloque y los errores recuperables.
- Validar integridad, idioma, omisiones y elementos protegidos.

**Resultado:** `data/translated/blocks_es.jsonl` validado.

### Fase 4 — Generación de PDF legible

- Componer el texto traducido respetando la estructura básica.
- Mantener fuentes y tamaños cuando sea viable.
- Redistribuir texto para evitar recortes y solapamientos.
- Reinsertar imágenes, listas y bloques de código.
- Añadir portada y pie de página configurables.
- Verificar visualmente una muestra y automáticamente todas las páginas.

**Resultado:** PDF traducido y legible en `output/`.

### Fase 5 — Salida Word editable

- Generar un documento `.docx` a partir del dataset traducido.
- Mantener jerarquías, listas, imágenes y estilos esenciales.
- Facilitar ajustes editoriales manuales posteriores.

**Resultado:** documento Word editable en `output/`.

### Fase 6 — Escala, OCR e idiomas adicionales

- Validar el procesamiento progresivamente hasta 1000 páginas.
- Incorporar OCR para documentos escaneados.
- Añadir detección automática de idioma.
- Incorporar nuevos idiomas de origen y destino.
- Añadir soporte específico para escritura RTL y sistemas CJK.
- Medir rendimiento, coste y calidad de traducción.

**Resultado:** flujo robusto para documentos heterogéneos y de gran tamaño.

## Criterios de éxito del laboratorio

El laboratorio se considerará completo cuando pueda:

1. Recibir un PDF compatible de entre 1 y 1000 páginas.
2. Convertirlo en datasets `raw`, `curated` y `translated` válidos y trazables.
3. Traducirlo al idioma seleccionado sin perder bloques ni alterar elementos protegidos.
4. Reanudar fases fallidas sin comenzar todo el proceso de nuevo.
5. Generar un PDF completo, legible y sin texto superpuesto o cortado.
6. Generar una versión Word editable.
7. Informar de errores y limitaciones sin producir silenciosamente un documento incompleto.

## Documento inicial de referencia

El primer caso de estudio es el PDF disponible en `input/`, compuesto por 284 páginas. Se utilizará para diseñar y validar las primeras fases del flujo antes de ampliar la cobertura a otros documentos e idiomas.
