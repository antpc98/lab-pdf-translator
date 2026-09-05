# Fase 1 — Plan de extracción estructurada

> Bitácora: 30/08/2026 — definición inicial de alcance, arquitectura, subtareas, validación y criterios de Done de la fase 1.

## 1. Objetivo

Transformar un PDF digital compatible en una representación `raw` completa, inmutable, trazable y reproducible, conforme a `schemas/document.schema.json`, sin corregir, traducir ni reinterpretar su contenido.

La fase termina con:

- `data/raw/document.json`: dataset documental validado.
- `assets/images/`: recursos binarios extraídos y deduplicados.
- Checkpoints temporales necesarios para reanudar una ejecución interrumpida.
- Logs y resumen de ejecución con páginas, bloques, recursos, advertencias, duración y estado.
- Evidencias automáticas y manuales suficientes para que el Team Leader valore el paso a `Done`.

## 2. Límites de la capa raw

La extracción describe lo que el motor observa; no corrige lo que el documento quiso decir.

Debe conservar:

- Secuencia Unicode entregada por el extractor.
- Página física de procedencia.
- Geometría, rotación y cajas PDF.
- Orden determinista y el índice original del motor cuando el contrato lo contemple.
- Tipografía disponible: familia, tamaño, estilos y propiedades representables.
- Recursos binarios y cada una de sus apariciones.
- Advertencias y estados parciales sin eliminar silenciosamente información.

No pertenece a esta fase:

- Unir párrafos separados o corregir guiones y espacios.
- Reconstruir semánticamente documentos multicolumna.
- Eliminar cabeceras o pies repetidos.
- Normalizar Unicode o corregir errores del texto.
- Traducir, aplicar glosarios o componer el PDF final.

El “orden de lectura” de esta fase será un orden técnico, estable y documentado. La interpretación semántica de columnas y continuidades pertenece a `curated`.

## 3. Arquitectura prevista

```text
scripts/extract.py
        │
        ▼
extraction/service.py        coordinación de la fase
        ├── pdf_reader.py    apertura, metadatos y páginas
        ├── page_parser.py   bloques, líneas, spans y geometría
        ├── classifier.py    clasificación inicial conservadora
        ├── assets.py        binarios, hashes y apariciones
        ├── ordering.py      orden determinista
        └── checkpoint.py    progreso y reanudación
                │
                ├── models/          representación y serialización
                ├── validation/      esquema y semántica
                └── observability/   logs y métricas
```

Los nombres concretos podrán ajustarse durante la implementación, pero las responsabilidades permanecerán separadas:

- Los scripts interpretan argumentos y devuelven códigos de salida.
- `extraction` conoce PyMuPDF y transforma sus resultados.
- `models` representa el contrato sin abrir PDFs.
- `validation` comprueba y nunca modifica el dataset.
- La persistencia escribe resultados temporales y publica el resultado final de forma atómica.
- Ningún módulo de extracción contiene traducción o renderizado.

## 4. Subtareas de desarrollo

### 1. Contrato de ejecución y CLI

- Definir argumentos: PDF, salida, selección de páginas, reanudación, sobrescritura y nivel de log.
- Integrarlos con `config/settings.yaml` sin duplicar reglas.
- Validar archivo, MIME, tamaño, cifrado, rango de 1 a 1000 páginas y permisos de lectura.
- Establecer códigos de salida y mensajes operacionales.

**Aceptación:** entradas válidas arrancan; rutas inseguras, PDFs incompatibles y opciones contradictorias fallan antes de escribir resultados.

### 2. Modelos y serialización raw

- Representar documento, página, bloque, línea, span, asset, aparición y warning.
- Serializar exclusivamente campos permitidos por el JSON Schema.
- Preservar números con una precisión máxima de cuatro decimales.
- Escribir JSON UTF-8 determinista y legible.

**Aceptación:** round-trip de los modelos sin pérdida y salida validada contra el contrato.

### 3. Inspección documental

- Calcular tamaño, SHA-256 y `document_id` antes de extraer.
- Leer metadatos, `CropBox`, `MediaBox`, rotación, etiquetas impresas cuando estén disponibles y número físico de páginas.
- Registrar nombre y versión exacta de PyMuPDF y fecha UTC de extracción.

**Aceptación:** el documento privado de referencia se reconoce con 284 páginas y el PDF sintético con su total esperado.

### 4. Extracción de texto y geometría

- Recorrer todas las páginas físicas.
- Extraer bloques, líneas y spans sin normalizar su texto.
- Conservar cajas, fuentes, tamaños, estilos, color y visibilidad cuando el motor los proporcione de forma fiable.
- Conservar páginas vacías y registrar limitaciones de extracción.

**Aceptación:** ninguna página desaparece; toda caja queda dentro de su página y todo texto conserva trazabilidad hasta un span.

### 5. Orden determinista

- Capturar el índice entregado por el extractor.
- Redondear geometría conforme al contrato.
- Ordenar bloques, líneas, spans y apariciones con las reglas versionadas.
- No presentar el orden geométrico como reconstrucción semántica multicolumna.

**Aceptación:** dos ejecuciones equivalentes generan las mismas secuencias e identificadores.

### 6. Clasificación inicial de bloques

- Reconocer de manera conservadora títulos, encabezados, párrafos, elementos de lista, código, imágenes, pies y números de página.
- Documentar señales utilizadas: tipografía, geometría y patrones mínimos.
- Usar `unknown` cuando no exista evidencia suficiente.
- No reescribir texto para forzar una clasificación.

**Aceptación:** cada bloque usa un valor permitido; los casos representativos tienen la clasificación esperada y los ambiguos no se inventan.

### 7. Extracción y gobierno de imágenes

- Extraer bytes, MIME, dimensiones, extensión y SHA-256.
- Nombrar el archivo físico a partir de `asset_id`.
- Deduplicar binarios idénticos y conservar apariciones separadas con página, caja, transformación y orden.
- Escribir recursos inicialmente en una ubicación temporal.

**Aceptación:** hashes coinciden con los archivos guardados; no hay referencias huérfanas ni duplicados físicos innecesarios.

### 8. Identificadores deterministas

- Reutilizar exclusivamente `models/identifiers.py`.
- Generar IDs después de fijar orden y geometría.
- Verificar namespace, versión y relaciones padre-hijo.
- Prohibir fórmulas de UUID duplicadas en el extractor.

**Aceptación:** todas las validaciones semánticas pasan y los IDs permanecen estables al repetir la extracción.

### 9. Persistencia atómica, checkpoints y reanudación

- Procesar por páginas o lotes según configuración.
- Guardar checkpoints versionados con identidad de entrada y configuración relevante.
- Reanudar solo si PDF, contrato, esquema de IDs, extractor y opciones compatibles coinciden.
- Rechazar checkpoints corruptos o pertenecientes a otra entrada.
- Publicar `document.json` y assets únicamente después de validar el conjunto; evitar resultados finales a medio escribir.

**Aceptación:** una interrupción simulada continúa sin duplicar páginas o recursos, y el resultado lógico coincide con una ejecución limpia. La fecha operacional puede variar; contenido e IDs no.

### 10. Validación y observabilidad

- Ejecutar JSON Schema y controles semánticos antes de publicar la salida.
- Registrar inicio, fin, duración, páginas procesadas/reutilizadas, bloques, spans, assets, advertencias y estado.
- Limitar errores mostrados conforme a configuración sin perder el resultado estructurado.
- Evitar texto completo o datos sensibles en logs por defecto.

**Aceptación:** un resultado inválido no se publica como completo y cada fallo tiene diagnóstico y código de salida.

### 11. Pruebas y muestras

- Pruebas unitarias por módulo y regla.
- Pruebas de contrato para serialización.
- Integración con PDF sintético reproducible.
- Regresión sobre las páginas físicas 19, 22 y 31 del caso privado.
- Ampliar la muestra con portada, página gráfica, definición, lista y contraportada ya identificadas en el manifiesto.
- Casos negativos: archivo inexistente, no PDF, protegido, checkpoint incompatible y escritura interrumpida.

**Aceptación:** pruebas repetibles, sin dependencia de orden accidental, incluidas en la barrera única y con cobertura global igual o superior al 90 %.

### 12. Documentación y entrega

- Documentar cada decisión relevante y cada limitación conocida.
- Actualizar CLI, configuración, estructura, contrato y troubleshooting cuando corresponda.
- Mantener bitácora de fecha y fase en todo módulo creado o modificado.
- Incorporar comandos, salida esperada y procedimiento de revisión visual.
- Preparar la migración a muestra pública conforme a `test-document-governance.md`.

**Aceptación:** una persona nueva puede instalar, extraer, interrumpir, reanudar, validar e interpretar la salida siguiendo solo la documentación.

## 5. Estrategia de reanudación

La reanudación se diseñará antes de implementar la escritura para evitar reconstruirla al final.

Cada checkpoint deberá asociarse al menos con:

- `source_sha256` y `document_id`.
- `schema_version` e `id_scheme_version`.
- Nombre y versión del extractor.
- Huella de las opciones que alteran la salida.
- Páginas completadas y estado de sus assets.
- Versión del formato de checkpoint.

El checkpoint es operacional y no forma parte de `document.json`. Puede reemplazarse durante el proceso. La capa `raw` final permanece inmutable.

## 6. Matriz inicial de validación visual y estructural

| Página física | Evidencia principal |
|---:|---|
| 1 | Portada, título y tipografía destacada. |
| 2 | Página gráfica sin texto extraíble. |
| 19 | Apertura de capítulo y comienzo de numeración impresa. |
| 22 | Texto y varias figuras. |
| 31 | Código, símbolos y hashes. |
| 100 | Definición y jerarquía tipográfica. |
| 200 | Lista numerada y recurso gráfico. |
| 284 | Contraportada. |

La numeración anterior es física y comienza en 1. Si cambia el documento de prueba, se sustituirá el manifiesto completo y no se trasladarán expectativas a ciegas.

## 7. Evidencias exigidas en el review

El review previo a `Done` incluirá:

- Comando exacto y código de salida de una extracción limpia.
- Comando y evidencia de una reanudación tras interrupción simulada.
- Resumen de páginas, bloques, spans, imágenes, warnings y duración.
- Hash del PDF y del `document.json` resultante.
- Resultado de validación estructural y semántica sin errores.
- Comparación de IDs entre dos ejecuciones.
- Inspección visual de las páginas de la matriz.
- Barrera automática completa en `PASS`.
- Estado Git limpio y commit identificable.
- Riesgos, limitaciones y deuda técnica expresamente registrados.

## 8. Definition of Done del Team Leader

La fase 1 puede pasar a `Done` cuando se cumplan simultáneamente estos criterios:

1. El 100 % de las páginas compatibles está representado, incluidas las vacías.
2. `data/raw/document.json` cumple JSON Schema y validación semántica.
3. El texto `raw` no ha sido normalizado, corregido ni traducido.
4. Geometría, tipografía, orden técnico y procedencia son trazables.
5. Todos los assets guardados coinciden con sus hashes y referencias.
6. Los IDs son estables al repetir una extracción equivalente.
7. La interrupción y reanudación no duplica ni pierde datos.
8. La escritura final es atómica y no presenta un dataset incompleto como válido.
9. Las páginas representativas superan comprobaciones automáticas y revisión visual.
10. La batería completa conserva al menos el 90 % de cobertura.
11. La barrera de calidad devuelve `RESULT: PASS` y código `0`.
12. Código, configuración y documentación mantienen separación de responsabilidades y bitácora `fecha — fase — actuación`.
13. No existen errores críticos o altos abiertos; los riesgos menores están aceptados y documentados.
14. La procedencia y licencia del documento son compatibles con el ámbito personal o público declarado.

Un resultado “parcial” puede ser útil para diagnóstico, pero no satisface por sí solo el `Done` de una extracción completa.

## 9. Convención de bitácora de código

Cada módulo nuevo o modificado en la fase utilizará este formato:

```python
"""Responsabilidad concreta del módulo.

Bitácora:
    2026-08-30 - Fase 1: creación inicial para <responsabilidad>.
    AAAA-MM-DD - Fase 1: cambio posterior y motivo.
"""
```

Los YAML, scripts de shell y documentos utilizarán el comentario equivalente de su formato. La bitácora explica evolución y decisiones; Git continúa siendo la autoridad sobre el detalle exacto de cada cambio.

## 10. Orden recomendado de implementación

1. CLI, inspección de entrada y modelos.
2. Extracción de página, texto y geometría.
3. Orden e identificadores.
4. Imágenes y apariciones.
5. Clasificación conservadora.
6. Persistencia temporal y atómica.
7. Checkpoints y reanudación.
8. Validación, observabilidad y CLI definitiva.
9. Pruebas de integración y revisión de muestras.
10. Documentación, quality gate y review de Team Leader.

No se iniciará la fase 2 hasta que el contrato `raw` pueda producirse y verificarse de extremo a extremo.
