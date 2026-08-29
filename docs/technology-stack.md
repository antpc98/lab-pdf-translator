# Selección de librerías

## Decisión

El entorno objetivo inicial es **CPython 3.14.7**. Las dependencias directas se fijan en `requirements.txt` para que el laboratorio parta de una combinación conocida y revisable.

La selección cubre únicamente extracción, validación, configuración y renderizado. Los motores de traducción y OCR se decidirán en las fases correspondientes.

## Dependencias de ejecución

### PyMuPDF 1.28.2

**Responsabilidad:** motor principal de lectura y extracción de PDF.

Se utilizará para:

- Abrir y recorrer documentos y páginas.
- Extraer bloques, líneas, spans, fuentes, tamaños, colores y coordenadas.
- Leer `CropBox`, `MediaBox`, rotación, metadatos y etiquetas de página.
- Identificar y extraer imágenes y sus apariciones.
- Renderizar páginas a imagen para inspección y pruebas visuales.
- Detectar documentos protegidos, dañados o parcialmente legibles.

No se utilizará para normalizar o traducir el texto de la capa `raw`.

**Motivo de elección:** proporciona información tipográfica y geométrica de bajo nivel, dispone de ruedas binarias para Python 3.14 en Windows y permite cubrir extracción y previsualización con un único motor.

**Licencia:** AGPL-3.0 o licencia comercial de Artifex. Es válida para este laboratorio, pero deberá revisarse antes de distribuir el sistema como producto cerrado o servicio propietario. Si ese escenario aparece, se evaluará una alternativa de licencia permisiva o una licencia comercial.

### jsonschema 4.26.0 con `format-nongpl`

**Responsabilidad:** validación estructural de datasets.

Se utilizará para:

- Comprobar que `schemas/document.schema.json` es un esquema válido.
- Validar datasets con `Draft202012Validator`.
- Activar explícitamente `FormatChecker` para UUID y fechas RFC 3339.
- Recoger todos los errores de una ejecución mediante validación iterativa.
- Confirmar que los ejemplos válidos pasan y los inválidos fallan.

El extra `format-nongpl` incorpora comprobadores de formato evitando dependencias opcionales GPL. La presencia del extra no activa por sí sola los formatos; el código deberá instanciar `FormatChecker` explícitamente.

**Motivo de elección:** implementa JSON Schema Draft 2020-12, coincide con el contrato existente y soporta Python 3.14.

**Licencia:** MIT.

### ReportLab 5.0.1

**Responsabilidad:** composición del PDF de salida.

Se utilizará para:

- Crear páginas y flujos de texto traducido.
- Registrar e incrustar fuentes.
- Dibujar texto, imágenes, fondos, cabeceras y pies.
- Crear la portada estándar y la numeración correcta.
- Controlar saltos de página y composición para evitar recortes y solapamientos.

PyMuPDF podrá inspeccionar y rasterizar el resultado, pero ReportLab será el generador principal del PDF traducido. Esta separación evita acoplar la extracción a la composición editorial.

**Motivo de elección:** biblioteca estable, orientada expresamente a generación de PDF y compatible con Python 3.14.

**Licencia:** BSD.

### python-docx-ng 2.1.0

**Responsabilidad:** generación de la salida Word (`.docx`).

Se utilizará para:

- Crear documentos editables.
- Aplicar estilos, jerarquías, listas y tablas.
- Insertar imágenes, cabeceras, pies y campos de numeración.
- Facilitar correcciones editoriales manuales posteriores.

El paquete se importa como `docx` y no puede instalarse junto a `python-docx`, porque ambos proporcionan el mismo paquete importable.

**Motivo de elección:** mantiene compatibilidad con la API de `python-docx`, declara soporte de Python 3.14 y añade campos, numeración, pies y otras capacidades útiles para este proyecto.

**Licencia:** MIT.

### Pillow 12.3.0

**Responsabilidad:** tratamiento de los recursos rasterizados.

Se utilizará para:

- Abrir y verificar imágenes extraídas.
- Consultar dimensiones, modo de color y formato.
- Convertir recursos a formatos compatibles con PDF o DOCX cuando sea necesario.
- Crear comparaciones y muestras para las pruebas visuales.

Aunque otras dependencias pueden instalar Pillow de forma transitiva, se declara como dependencia directa porque el proyecto utilizará su API.

**Licencia:** MIT-CMU.

### PyYAML 6.0.3

**Responsabilidad:** configuración del flujo y glosarios.

Se utilizará para leer `config/settings.yaml` y `config/glossary.yaml`. La carga se realizará con `yaml.safe_load`; no se aceptará deserialización arbitraria mediante `yaml.load`.

**Motivo de elección:** solución estable, con soporte Unicode y ruedas binarias para Python 3.14 en Windows.

**Licencia:** MIT.

## Matriz de responsabilidades

| Capacidad | Librería principal | Apoyo o verificación |
|---|---|---|
| Extracción de PDF | PyMuPDF | JSON Schema y validaciones semánticas propias |
| Fuentes, spans y `bbox` | PyMuPDF | Contrato `raw` |
| Imágenes y apariciones | PyMuPDF | Pillow |
| Validación estructural | jsonschema | Pruebas semánticas propias |
| Generación de PDF | ReportLab | PyMuPDF para inspección visual |
| Generación de DOCX | python-docx-ng | Word o LibreOffice para inspección visual |
| Configuración YAML | PyYAML | Validación propia de configuración |

## Dependencias no incluidas todavía

- **OCR:** Tesseract u otros motores se evaluarán en la fase 6.
- **Traducción:** proveedor, SDK y cliente HTTP se elegirán en la fase 3.
- **Detección de idioma:** se elegirá cuando se implemente soporte multilingüe automático.
- **Procesamiento de tablas especializado:** solo se añadirá si PyMuPDF no cubre los casos reales.
- **PyMuPDF4LLM:** no se necesita para el contrato geométrico `raw` y añadiría una abstracción innecesaria.

## Política de versiones

- `requirements.txt` fija versiones directas exactas mientras se construye el primer flujo reproducible.
- Las dependencias transitivas serán resueltas por `pip`; antes de una entrega estable se generará un archivo de bloqueo con hashes.
- Las actualizaciones se harán de una en una y deberán ejecutar pruebas de extracción, contrato y renderizado.
- Un cambio de versión del extractor se registrará en `extraction.extractor_version`.
- Si una actualización modifica el orden o los IDs generados, deberá incrementarse `id_scheme_version`.

## Verificación de compatibilidad

El 29/08/2026 se ejecutó una resolución en seco de `requirements.txt` para Windows y CPython 3.14 mediante `pip --dry-run --python-version 3.14 --only-binary=:all:`. Todas las dependencias directas y transitivas encontraron distribuciones binarias compatibles. La operación no instaló paquetes ni modificó el entorno de Python.

Referencias oficiales consultadas:

- [PyMuPDF en PyPI](https://pypi.org/project/PyMuPDF/)
- [jsonschema en PyPI](https://pypi.org/project/jsonschema/)
- [ReportLab en PyPI](https://pypi.org/project/reportlab/)
- [python-docx-ng en PyPI](https://pypi.org/project/python-docx-ng/)
- [Pillow en PyPI](https://pypi.org/project/Pillow/)
- [PyYAML en PyPI](https://pypi.org/project/PyYAML/)

## Instalación prevista

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

La instalación debe realizarse dentro de un entorno virtual. `requirements.txt` no incluye todavía herramientas de desarrollo como el framework de pruebas o el linter; se seleccionarán al preparar la subtarea de pruebas unitarias.

## Criterios de aceptación

La selección se considera terminada cuando:

1. Cada responsabilidad tiene una librería principal y una justificación.
2. Las dependencias directas declaran compatibilidad con Python 3.14 o distribuyen artefactos compatibles.
3. Las versiones están fijadas en `requirements.txt`.
4. Las licencias y riesgos relevantes están documentados.
5. OCR y traducción permanecen fuera del alcance de esta decisión.
6. `pip` resuelve todas las dependencias para CPython 3.14 sin compilaciones locales.

Los seis criterios de selección están cumplidos. La creación del entorno virtual, la instalación efectiva y una prueba de importaciones pertenecen a la siguiente tarea: crear la estructura mínima del proyecto y su configuración.
