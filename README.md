# Lab PDF Translator

Laboratorio para construir un flujo reproducible de extracción, gobierno, traducción y reconstrucción de documentos.

El sistema transformará cada documento de entrada en un conjunto de datos estructurado y trazable. Sobre ese dataset se aplicarán reglas de normalización y traducción y, finalmente, se generará un documento cómodo de leer.

> Estado actual: definición y diseño. La primera fase de desarrollo será la extracción estructurada del PDF de referencia incluido en `input/`.

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

## Arquitectura prevista

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
├── src/
│   ├── models/            # Esquemas del documento y sus bloques
│   ├── extraction/        # Lectura y extracción de documentos
│   ├── processing/        # Limpieza, clasificación y normalización
│   ├── translation/       # Motores y reglas de traducción
│   ├── validation/        # Controles de calidad
│   └── rendering/         # Generación de PDF y DOCX
├── scripts/               # Puntos de entrada del flujo
├── output/                # Documentos generados
├── tests/                 # Pruebas automáticas y muestras
├── requirements.txt
└── README.md
```

Esta estructura representa el diseño objetivo y se creará progresivamente durante las fases de desarrollo.

## Fases de desarrollo

### Fase 0 — Definición y entorno

- Definir el esquema de datos y las reglas de identificación.
- Elegir las librerías de extracción, validación y renderizado.
- Crear la estructura mínima del proyecto y su configuración.
- Preparar pruebas unitarias y muestras representativas.

**Resultado:** contrato de datos versionado y proyecto ejecutable en local.

### Fase 1 — Extracción estructurada

Convertir el PDF de referencia en una representación JSON sin modificar su contenido.

- Detectar todas sus páginas.
- Extraer texto y orden de lectura.
- Extraer coordenadas (`bbox`).
- Extraer fuentes, tamaños y estilos.
- Identificar y guardar imágenes.
- Reconocer inicialmente títulos, párrafos, listas y bloques de código.
- Generar identificadores únicos y estables.
- Guardar un JSON válido.
- Permitir repetir o reanudar la extracción.

**Resultado:** `data/raw/document.json` y recursos asociados.

**Validación inicial:** páginas 19, 22 y 31, además de páginas representativas con código, imágenes y listas.

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
