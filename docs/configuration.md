# Guía de configuración

> Bitácora: 30/08/2026 — implementados el cargador seguro, la precedencia local y las validaciones automáticas.

## 1. Objetivo

La configuración permite cambiar el comportamiento del pipeline sin editar el código Python.

Existen dos archivos base:

- `config/settings.yaml`: ejecución, rutas, validación y salida.
- `config/glossary.yaml`: términos y decisiones lingüísticas.

Ambos utilizan YAML, un formato de texto basado en indentación. Los espacios son significativos; se usarán dos espacios por nivel y nunca tabulaciones.

## 2. Cómo leer YAML

Un valor sencillo:

```yaml
max_pages: 1000
```

Un grupo de valores:

```yaml
pipeline:
  source_language: en
  target_language: es
```

Una lista:

```yaml
fallback_fonts:
  - Arial
  - DejaVu Sans
```

Un valor vacío explícito:

```yaml
provider: null
```

Un comentario comienza con `#` y no afecta al programa.

## 3. Reglas generales

- Las rutas se interpretan desde la raíz del repositorio.
- Los nombres de idioma usan códigos BCP 47 simples en esta versión, como `en` y `es`.
- Los valores booleanos son `true` o `false`.
- `null` indica que todavía no existe un valor.
- Una lista vacía `[]` significa «sin restricción específica» cuando así lo indique esta guía.
- La configuración base puede versionarse porque no contiene secretos.
- Las claves API se proporcionarán mediante variables de entorno, nunca en YAML.

## 4. Precedencia futura

Cuando exista el cargador de configuración, la prioridad será, de menor a mayor:

```text
config/settings.yaml
        ↓ sobrescribe
config/settings.local.yaml
        ↓ sobrescribe
variables de entorno permitidas
        ↓ sobrescribe
argumentos explícitos de terminal
```

`settings.local.yaml` está ignorado por Git y permitirá adaptar rutas o comportamiento a una máquina concreta. No existe todavía porque la configuración base es suficiente.

La configuración efectiva utilizada en cada ejecución deberá registrarse en el log, ocultando cualquier secreto.

## 5. Referencia de `settings.yaml`

### `project`

Metadatos generales de la ejecución.

```yaml
project:
  name: lab-pdf-translator
  environment: development
```

| Campo | Tipo | Valor inicial | Función |
|---|---|---|---|
| `name` | texto | `lab-pdf-translator` | Identifica el proyecto en logs e informes. |
| `environment` | texto | `development` | Distingue desarrollo de futuros entornos de prueba o producción. |

`environment` no cambia por sí solo el comportamiento. Sirve como etiqueta y las diferencias deben declararse explícitamente.

### `contract`

Conecta el pipeline con el contrato de datos.

```yaml
contract:
  schema_path: schemas/document.schema.json
  schema_version: 1.0.0
  id_scheme_version: 1
```

| Campo | Tipo | Restricción | Función |
|---|---|---|---|
| `schema_path` | ruta | Archivo existente | JSON Schema de la capa `raw`. |
| `schema_version` | texto SemVer | `1.0.0` | Versión que debe escribir y aceptar el extractor. |
| `id_scheme_version` | entero | `>= 1` | Versión del algoritmo determinista de IDs. |

La configuración y el esquema deben coincidir. Si no coinciden, la ejecución debe detenerse antes de procesar documentos.

### `paths`

Define dónde lee y escribe cada fase.

```yaml
paths:
  input_dir: input
  raw_data_dir: data/raw
  curated_data_dir: data/curated
  translated_data_dir: data/translated
  image_dir: assets/images
  output_dir: output
  log_dir: logs
```

| Campo | Lectura/escritura | Contenido |
|---|---|---|
| `input_dir` | Solo lectura | Documentos originales. |
| `raw_data_dir` | Escritura en extracción | JSON inmutable. |
| `curated_data_dir` | Escritura en procesamiento | Datos normalizados. |
| `translated_data_dir` | Escritura en traducción | Datos traducidos. |
| `image_dir` | Escritura en extracción | Binarios identificados por hash. |
| `output_dir` | Escritura en renderizado | PDF y DOCX finales. |
| `log_dir` | Escritura transversal | Logs operacionales. |

Reglas de seguridad futuras:

- Las rutas se resolverán y comprobarán antes de escribir.
- Ninguna ruta de salida podrá coincidir con `input_dir`.
- No se aceptarán rutas de salida fuera del proyecto salvo configuración local explícita.
- El pipeline creará directorios ausentes, pero no borrará árboles completos.

### `pipeline`

Controla decisiones compartidas por todas las fases.

```yaml
pipeline:
  source_language: en
  target_language: es
  detect_source_language: false
  max_pages: 1000
  batch_size: 25
  resume: true
  overwrite: false
  fail_fast: false
```

| Campo | Tipo | Valor inicial | Comportamiento |
|---|---|---|---|
| `source_language` | texto | `en` | Idioma declarado del documento inicial. |
| `target_language` | texto | `es` | Idioma de traducción. |
| `detect_source_language` | booleano | `false` | Si es `true`, un detector futuro propondrá el idioma. |
| `max_pages` | entero 1–1000 | `1000` | Límite de seguridad por documento. |
| `batch_size` | entero positivo | `25` | Páginas o segmentos procesados antes de guardar checkpoint. |
| `resume` | booleano | `true` | Reutiliza checkpoints compatibles. |
| `overwrite` | booleano | `false` | Impide sustituir resultados existentes sin autorización. |
| `fail_fast` | booleano | `false` | Si es `false`, intenta recoger varios errores antes de terminar. |

`resume` solo reutilizará resultados si coinciden hash de entrada, versión del contrato, versión del extractor y configuración relevante.

`overwrite: false` es la opción segura. Activarlo no autoriza a borrar el PDF original ni otros documentos.

### `extraction`

Controla qué conserva la capa `raw`.

```yaml
extraction:
  engine: pymupdf
  include_text: true
  include_images: true
  include_invisible_text: true
  preserve_raw_unicode: true
  coordinate_precision: 4
  page_selection: []
```

| Campo | Tipo | Valor inicial | Función |
|---|---|---|---|
| `engine` | enumeración | `pymupdf` | Adaptador utilizado para leer PDF. |
| `include_text` | booleano | `true` | Conserva bloques, líneas y spans. |
| `include_images` | booleano | `true` | Extrae recursos y apariciones. |
| `include_invisible_text` | booleano | `true` | Mantiene texto no visible para auditoría. |
| `preserve_raw_unicode` | booleano | `true` | Prohíbe normalización Unicode en `raw`. |
| `coordinate_precision` | entero | `4` | Decimales de las coordenadas canónicas. |
| `page_selection` | lista de enteros | `[]` | Vacía procesa todas las páginas; con valores procesa solo esas páginas físicas. |

En ejecuciones de producción del dataset completo, `include_text`, `include_images`, `include_invisible_text` y `preserve_raw_unicode` deben permanecer en `true` para cumplir el contrato. `page_selection` se utilizará principalmente en desarrollo y pruebas.

### `validation`

Controla las barreras de calidad.

```yaml
validation:
  schema_enabled: true
  format_checker_enabled: true
  semantic_checks_enabled: true
  stop_on_schema_error: true
  max_reported_errors: 100
```

| Campo | Tipo | Valor inicial | Función |
|---|---|---|---|
| `schema_enabled` | booleano | `true` | Valida el JSON contra Draft 2020-12. |
| `format_checker_enabled` | booleano | `true` | Comprueba UUID y fechas, además de tipos. |
| `semantic_checks_enabled` | booleano | `true` | Comprueba relaciones que JSON Schema no expresa. |
| `stop_on_schema_error` | booleano | `true` | Impide avanzar si la estructura no es válida. |
| `max_reported_errors` | entero positivo | `100` | Limita el tamaño del informe sin ocultar el estado fallido. |

Las validaciones semánticas incluirán:

- `page_count == len(pages)`.
- Páginas consecutivas y únicas.
- IDs consistentes con sus fórmulas.
- Cajas dentro de los límites.
- Órdenes únicos y consecutivos.
- Recursos referenciados existentes.
- Hashes y rutas de recursos coherentes.

Desactivar validaciones solo será aceptable para diagnóstico local. Una capa no se publicará como válida si no supera sus controles.

### `translation`

Reserva la configuración de la fase 3.

```yaml
translation:
  enabled: false
  provider: null
  glossary_path: config/glossary.yaml
```

| Campo | Estado inicial | Función |
|---|---|---|
| `enabled` | `false` | Evita ejecutar una fase todavía no implementada. |
| `provider` | `null` | Se definirá al seleccionar motor de traducción. |
| `glossary_path` | Ruta al glosario | Reglas terminológicas del par de idiomas. |

No se almacenará una clave API en `provider` ni en ningún otro campo YAML.

### `rendering.pdf`

Configura la futura salida PDF.

```yaml
rendering:
  pdf:
    enabled: true
    engine: reportlab
    preserve_font_family: true
    preserve_font_size: true
    allow_text_reflow: true
    fallback_fonts:
      - Arial
      - DejaVu Sans
```

| Campo | Función |
|---|---|
| `enabled` | Habilita la salida PDF cuando exista el renderizador. |
| `engine` | Selecciona ReportLab. |
| `preserve_font_family` | Intenta reutilizar la familia original. |
| `preserve_font_size` | Intenta conservar el tamaño original. |
| `allow_text_reflow` | Permite redistribuir texto para evitar cortes. |
| `fallback_fonts` | Familias candidatas cuando la original no está disponible. |

Las fuentes de fallback deben comprobarse en la máquina antes de usarse. Declarar una familia no instala ni concede licencia para incrustarla.

### `rendering.docx`

```yaml
rendering:
  docx:
    enabled: false
    engine: python-docx-ng
```

Permanece desactivado hasta la fase 5. El nombre del motor corresponde al paquete instalable; el código se importará como `docx`.

### `rendering.cover`

```yaml
rendering:
  cover:
    enabled: true
    title: Traducción de documento
    subtitle: null
```

Define la portada editorial. `subtitle: null` omite el subtítulo. En el futuro podrán añadirse plantilla, logo, autor y metadatos sin modificar el dataset traducido.

### `rendering.footer`

```yaml
rendering:
  footer:
    enabled: true
    show_page_number: true
    template: "Página {page_number} de {page_count}"
```

Variables admitidas inicialmente:

- `{page_number}`: número de la página final.
- `{page_count}`: total de páginas finales.

La numeración final puede diferir del PDF original si se añade portada. El renderizador debe calcularla después de componer el documento.

### `logging`

```yaml
logging:
  level: INFO
  console: true
  file: true
  file_name: pipeline.log
```

| Campo | Valores | Función |
|---|---|---|
| `level` | `DEBUG`, `INFO`, `WARNING`, `ERROR` | Nivel mínimo registrado. |
| `console` | booleano | Muestra progreso en terminal. |
| `file` | booleano | Escribe también en `paths.log_dir`. |
| `file_name` | nombre seguro | Archivo de log. |

No se registrarán texto completo sensible, secretos o respuestas integrales del proveedor de traducción por defecto.

## 6. Referencia de `glossary.yaml`

El glosario mantiene coherencia terminológica.

```yaml
version: 1
source_language: en
target_language: es
case_sensitive: false
terms: []
```

### Metadatos

| Campo | Función |
|---|---|
| `version` | Versión interna del glosario. |
| `source_language` | Idioma de los términos originales. |
| `target_language` | Idioma de las traducciones. |
| `case_sensitive` | Distingue mayúsculas y minúsculas al buscar términos. |
| `terms` | Lista ordenada de reglas terminológicas. |

### Forma futura de un término

```yaml
terms:
  - source: smart contract
    target: contrato inteligente
    mode: preferred
    notes: Término técnico acordado para todo el documento.
```

Modos previstos:

- `preferred`: utilizar la traducción indicada de forma consistente.
- `protected`: no traducir el término original.
- `forbidden`: señalar como error una traducción concreta; requerirá un campo adicional cuando se implemente.

El glosario está vacío porque todavía no se ha realizado el análisis terminológico del libro. Los comentarios son ejemplos, no reglas activas.

## 7. Configuración efectiva y reproducibilidad

Cada ejecución deberá calcular una representación canónica de las opciones que afectan al resultado. Esa representación permitirá:

- Decidir si un checkpoint puede reutilizarse.
- Explicar por qué dos ejecuciones difieren.
- Registrar la configuración sin depender del archivo actual.
- Invalidar resultados cuando cambien reglas importantes.

Cambios que deben invalidar la extracción existente:

- Motor o versión del extractor.
- Versión del contrato o IDs.
- Precisión de coordenadas.
- Inclusión de texto o imágenes.
- Selección de páginas.

Cambios puramente operacionales, como mostrar logs en consola, no deben cambiar los IDs ni invalidar el dataset.

## 8. Errores de configuración

El futuro cargador debe fallar antes de procesar si encuentra:

- YAML inválido.
- Campo obligatorio ausente.
- Campo desconocido.
- Tipo incorrecto.
- Idioma vacío o incompatible con el glosario.
- `max_pages` fuera de 1–1000.
- `batch_size <= 0`.
- Precisión distinta de la definida por el contrato.
- Ruta de esquema inexistente.
- Directorio de salida igual al de entrada.
- Motor no soportado.
- Plantilla de pie con variables desconocidas.

El mensaje debe indicar archivo, campo, valor recibido y corrección esperada, sin mostrar secretos.

## 9. Ejemplos de uso futuro

Procesar el documento completo:

```yaml
extraction:
  page_selection: []
```

Probar únicamente las páginas 19, 22 y 31:

```yaml
extraction:
  page_selection:
    - 19
    - 22
    - 31
```

Cambiar el destino a francés cuando exista soporte:

```yaml
pipeline:
  source_language: en
  target_language: fr
```

Activar diagnóstico detallado:

```yaml
logging:
  level: DEBUG
```

## 10. Qué está activo actualmente

El cargador de `src/lab_pdf_translator/config.py` ya lee los YAML mediante `yaml.safe_load`, combina opcionalmente `settings.local.yaml` y valida tipos, versiones, rutas, idiomas, glosario y límites. `scripts/validate_phase0.py` ejecuta estos controles como parte del cierre automático de la fase 0.

El estado inicial es deliberadamente seguro:

- Traducción desactivada.
- DOCX desactivado.
- Sobrescritura desactivada.
- Validación activada.
- Preservación `raw` activada.
- Límite de 1000 páginas.
- Reanudación activada para cuando existan checkpoints.

## 11. Criterios de aceptación de la configuración base

La configuración base se considera definida cuando:

1. Los YAML tienen sintaxis válida.
2. Cada ruta y opción tiene una responsabilidad documentada.
3. Los valores iniciales respetan el contrato `raw`.
4. Las fases no implementadas están desactivadas cuando podrían llamar servicios externos.
5. No existen secretos ni datos específicos de una máquina.
6. Git ignora la futura configuración local privada.
7. Se documentan precedencia, errores y efecto sobre reproducibilidad.

Los siete criterios están cubiertos por el cargador y por las pruebas de `tests/test_configuration.py`. Toda opción nueva deberá ampliar tanto su validación como su prueba y esta referencia.
