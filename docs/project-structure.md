# Guía de estructura y procesamiento

> Bitácora: 30/08/2026 — estructura revisada tras implementar modelos de identidad, configuración y validación de la fase 0.
>
> Bitácora: 30/08/2026 — Fase 1: incorporado el plan modular y los límites arquitectónicos de extracción.

## 1. Qué representa este proyecto

`lab-pdf-translator` no traduce directamente un PDF y lo sobrescribe. Utiliza un pipeline por capas:

```text
PDF original
    ↓ extracción
dataset raw
    ↓ normalización y gobierno
dataset curated
    ↓ traducción y validación
dataset translated
    ↓ composición
PDF y DOCX finales
```

Separar el proceso permite inspeccionar cada resultado, repetir solo una fase y saber siempre de dónde procede cada texto.

## 2. Principio fundamental: archivos frente a código

El repositorio separa:

- **Entradas:** archivos entregados al pipeline.
- **Datos intermedios:** representación estructurada de los documentos.
- **Recursos:** imágenes y otros binarios extraídos.
- **Configuración:** decisiones que pueden cambiar sin modificar código.
- **Código:** comportamiento reutilizable del sistema.
- **Scripts:** comandos pequeños para iniciar cada fase.
- **Pruebas:** evidencia de que el comportamiento es correcto.
- **Salidas:** documentos generados para el usuario.

Esta separación evita mezclar el PDF original, el código y los resultados generados.

## 3. Vista completa de la estructura

```text
lab-pdf-translator/
├── .gitignore
├── README.md
├── requirements.txt
├── input/
├── data/
│   ├── raw/
│   ├── curated/
│   └── translated/
├── assets/
│   └── images/
├── config/
│   ├── settings.yaml
│   └── glossary.yaml
├── schemas/
│   ├── document.schema.json
│   └── examples/
├── docs/
│   ├── data-contract.md
│   ├── technology-stack.md
│   ├── project-structure.md
│   └── configuration.md
├── src/
│   └── lab_pdf_translator/
│       ├── models/
│       ├── extraction/
│       ├── processing/
│       ├── translation/
│       ├── validation/
│       └── rendering/
├── scripts/
├── tests/
│   └── fixtures/
├── output/
└── logs/
```

## 4. Recorrido de un documento

### Paso 1: entrada

El usuario deposita un documento en `input/`. El archivo es una fuente y no debe modificarse.

El futuro comando de extracción:

1. Lee la configuración.
2. Calcula el SHA-256 del archivo.
3. Genera `document_id`.
4. Comprueba tamaño, tipo MIME, protección y número de páginas.
5. Rechaza o informa de entradas que incumplan los límites configurados.

### Paso 2: extracción raw

El módulo `extraction` utiliza PyMuPDF para leer páginas, geometría, bloques, líneas, spans, fuentes e imágenes.

El módulo `models` convierte esa información en la forma interna acordada. El módulo `validation` comprueba el resultado contra `schemas/document.schema.json`.

La salida se guarda en `data/raw/`. Las imágenes se guardan en `assets/images/` y el dataset conserva sus referencias.

La capa `raw` es inmutable: si algo se interpreta mal, se corrige en la siguiente capa o se repite la extracción con otra versión. No se modifica manualmente.

### Paso 3: normalización curated

El módulo `processing` recibe exclusivamente datos `raw` válidos. Entre sus futuras responsabilidades estarán:

- Unir líneas que pertenecen al mismo párrafo.
- Detectar encabezados y pies repetidos.
- Reconstruir el orden semántico de varias columnas.
- Clasificar elementos dudosos.
- Proteger código, cifras, fórmulas y enlaces.
- Preparar segmentos con contexto suficiente para traducir.

El resultado se guarda en `data/curated/`. Cada registro conserva referencias a sus IDs `raw`.

### Paso 4: traducción

El módulo `translation` utiliza el idioma de origen, el idioma de destino y el glosario. El motor de traducción todavía no está seleccionado.

La salida se guarda en `data/translated/` y conserva:

- Texto original.
- Texto traducido.
- Estado de la operación.
- Motor y versión.
- Reglas de glosario aplicadas.
- Advertencias y referencias a `curated` y `raw`.

### Paso 5: renderizado

El módulo `rendering` consume únicamente datasets traducidos y validados.

- ReportLab generará el PDF.
- python-docx-ng generará el documento Word.
- Pillow ayudará a verificar y convertir imágenes.
- PyMuPDF rasterizará páginas generadas para la inspección visual.

Los documentos finales se guardan en `output/`. Nunca se escriben en `input/`.

### Paso 6: observabilidad

Cada ejecución escribirá información operacional en `logs/`: inicio, fin, configuración efectiva, páginas procesadas, duración, advertencias y errores.

Los logs ayudan a diagnosticar el pipeline, pero no forman parte del contrato documental y Git no los versiona.

## 5. Responsabilidad de cada ruta

### `input/`

Contiene documentos originales.

Reglas:

- El pipeline abre los archivos en modo lectura.
- No se renombran ni sobrescriben automáticamente.
- Su hash, no su nombre, determina la identidad documental.
- Un cambio de cualquier byte produce otro `document_id`.

### `data/raw/`

Contiene la representación inmutable producida por extracción.

Debe responder: «¿qué observó el extractor en el archivo original?». No responde todavía: «¿qué significa este contenido?».

Git conserva la carpeta, pero ignora los datasets generados porque pueden ser grandes y reproducibles.

### `data/curated/`

Contiene datos normalizados y gobernados. Aquí se corrige estructura, no el significado original.

Debe responder: «¿cómo debe organizarse este contenido para traducirlo con seguridad?».

### `data/translated/`

Contiene traducciones y su trazabilidad. No contiene el documento visual final.

Debe responder: «¿qué traducción aprobada corresponde a cada segmento gobernado?».

### `assets/images/`

Contiene recursos extraídos. El nombre físico debe derivarse de `asset_id` para evitar duplicados y colisiones.

Una imagen binaria puede tener varias apariciones en el documento. El binario se guarda una vez; posiciones y transformaciones permanecen en el dataset.

### `config/`

Contiene comportamiento modificable sin editar Python.

- `settings.yaml`: funcionamiento general del pipeline.
- `glossary.yaml`: decisiones terminológicas.
- `settings.local.yaml`: futura configuración privada local; Git la ignora.

La configuración no debe contener claves API ni contraseñas. Los secretos se suministrarán mediante variables de entorno.

### `schemas/`

Contiene contratos de datos independientes del código.

- `document.schema.json`: contrato `raw` 1.0.0.
- `examples/`: ejemplos que deben ser aceptados o rechazados.

El esquema es la autoridad sobre la forma externa del dataset. Los modelos Python deben adaptarse al esquema, no crear silenciosamente otro contrato.

### `docs/`

Contiene decisiones duraderas que no caben en el README.

- `data-contract.md`: semántica del dataset `raw`.
- `technology-stack.md`: librerías y licencias.
- `project-structure.md`: esta guía.
- `configuration.md`: referencia de configuración.
- `phase-1-extraction-plan.md`: arquitectura, subtareas, evidencias y Definition of Done de la extracción.

### `src/lab_pdf_translator/`

Es el paquete Python importable. Usar un paquete dentro de `src/` evita que las pruebas importen accidentalmente archivos desde la raíz y obliga a que la instalación sea correcta.

La lógica de negocio debe vivir aquí, no en `scripts/`.

### `models/`

Representará entidades y tipos internos. Su función será convertir entre objetos Python y JSON conforme al contrato.

No extrae PDF, no traduce y no escribe documentos.

### `extraction/`

Conecta el mundo externo con la capa `raw`.

Responsabilidades futuras:

- Abrir documentos.
- Recorrer páginas.
- Extraer texto, geometría, fuentes y recursos.
- Aplicar orden determinista.
- Generar IDs.
- Informar de errores sin perder páginas.

No normaliza texto ni decide traducciones.

### `processing/`

Transforma `raw` en `curated`. Contiene reglas de limpieza, clasificación, orden semántico y segmentación.

No modifica los archivos `raw` existentes.

### `translation/`

Define una interfaz independiente del proveedor. Gestionará lotes, contexto, glosarios, reintentos y respuestas.

No debe conocer detalles de ReportLab o DOCX.

### `validation/`

Centraliza controles compartidos:

- Validación JSON Schema.
- Restricciones geométricas que JSON Schema no expresa.
- Relaciones entre IDs y recursos.
- Integridad antes y después de traducir.
- Informes de errores utilizables por scripts y pruebas.

### `rendering/`

Convierte datos validados en documentos visuales. Su entrada son datasets, no el PDF original.

La separación permite generar PDF y DOCX desde la misma traducción.

### `scripts/`

Contendrá adaptadores de terminal. Un script puede leer argumentos, cargar configuración, llamar al paquete y seleccionar el código de salida.

No debe contener algoritmos de extracción, reglas de traducción o composición reutilizable.

### `tests/`

Contendrá pruebas unitarias, de contrato, integración y regresión visual.

`tests/fixtures/` almacena manifiestos y generadores de muestras pequeñas. Los archivos grandes y resultados temporales se generan durante la prueba o permanecen fuera de Git.

### `output/`

Contiene documentos finales. Se considera una carpeta de productos generados y Git ignora su contenido.

### `logs/`

Contiene evidencia operacional de ejecuciones locales. No almacena el dataset ni sustituye las advertencias estructuradas del contrato.

## 6. Dependencias entre módulos

El sentido permitido es:

```text
scripts
  └── extraction / processing / translation / rendering
          ├── models
          └── validation
```

Reglas de acoplamiento:

- `models` no depende de motores externos de PDF o traducción.
- `extraction` puede depender de PyMuPDF, `models` y `validation`.
- `processing` trabaja con modelos y no abre el PDF.
- `translation` no depende de renderizadores.
- `rendering` no invoca motores de traducción.
- `validation` no modifica datos mientras los comprueba.
- Los scripts coordinan, pero no implementan reglas.

## 7. Qué se versiona y qué no

Se versionan:

- Código y configuración base.
- Contratos y ejemplos pequeños.
- Documentación.
- Pruebas y fixtures pequeños.
- Archivos marcadores que mantienen carpetas vacías.

No se versionan automáticamente:

- `.venv/`.
- Cachés de Python y herramientas.
- Logs.
- Datasets generados.
- Imágenes extraídas.
- PDF y DOCX finales.
- Configuración local y secretos.

El PDF inicial ya está versionado como caso de estudio; esta regla no altera archivos que Git ya conoce.

## 8. Estados de una ejecución

Una fase puede terminar:

- `complete`: todos los elementos esperados fueron procesados.
- `partial`: existe un resultado utilizable con fallos explícitos.
- `failed`: no puede habilitar la siguiente fase.

Una fase posterior solo debe consumir entradas válidas. `fail_fast: false` permite recoger varios errores antes de terminar; no permite ocultarlos.

## 9. Cómo crecerá la estructura

La estructura actual implementa la infraestructura transversal de la fase 0: configuración, identificadores deterministas, validación estructural y semántica y automatización de aceptación. Las fases funcionales de extracción, transformación, traducción y renderizado siguen delimitadas, pero aún no están implementadas.

El crecimiento esperado es:

1. Implementar extracción utilizando los IDs ya disponibles.
2. Implementar procesamiento `curated`.
3. Incorporar proveedor de traducción.
4. Implementar renderizadores.
5. Añadir OCR y capacidades multilingües avanzadas.

Cada incorporación debe respetar las fronteras anteriores. Si una necesidad no encaja, primero se documenta la decisión y después se modifica la estructura.

## 10. Criterios de aceptación de la estructura mínima

La estructura mínima se considera creada cuando:

1. Existen todas las capas de datos y salida.
2. Existe el paquete importable y cada dominio tiene un espacio propio.
3. Existen configuraciones base sin secretos.
4. Los artefactos generados y el entorno virtual están ignorados por Git.
5. El README enlaza las guías detalladas.
6. La sintaxis de los YAML es válida.
7. Las responsabilidades y límites están documentados.

La existencia de una carpeta no significa que su funcionalidad esté implementada. El estado real de cada fase se mantiene en el README.
