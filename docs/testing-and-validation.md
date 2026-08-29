# Pruebas y validación automática

> Bitácora: 30/08/2026 — primera estrategia verificable de calidad y cierre de la fase 0.

## 1. Objetivo

Esta batería demuestra que la base del proyecto es reproducible antes de iniciar la extracción. Comprueba el contrato `raw`, sus identificadores, la configuración y una selección representativa del PDF real. Las pruebas no afirman todavía que el pipeline traduzca o reconstruya documentos: esas capacidades pertenecen a fases posteriores.

La calidad se divide en cuatro niveles:

1. **Pruebas unitarias:** funciones de IDs, carga de configuración y reglas semánticas aisladas.
2. **Pruebas de contrato:** validez del propio JSON Schema y aceptación o rechazo de sus ejemplos.
3. **Pruebas de integración:** lectura de un PDF sintético y de páginas elegidas del documento real mediante PyMuPDF.
4. **Validación de aceptación:** un único comando reúne los controles necesarios para autorizar el cierre de la fase 0 o una futura integración continua.

## 2. Componentes desarrollados

| Componente | Responsabilidad |
|---|---|
| `models/identifiers.py` | SHA-256 y UUID v5 deterministas conforme al contrato. |
| `config.py` | Carga YAML segura, superposición local y comprobaciones de coherencia. |
| `validation/schema.py` | Validación Draft 2020-12 con formatos UUID y fecha-hora. |
| `validation/semantic.py` | IDs, orden, geometría y relaciones que JSON Schema no puede expresar por sí solo. |
| `validation/automation.py` | Orquestación sin efectos laterales y reporte uniforme de controles. |
| `scripts/validate_phase0.py` | Interfaz de terminal y códigos de salida aptos para automatización. |
| `scripts/quality_gate.py` | Une dependencias, pruebas, cobertura y aceptación en una decisión obligatoria. |
| `scripts/run_quality_gate.cmd` | Prepara y activa automáticamente el entorno Windows antes de ejecutar la barrera. |
| `tests/` | Pruebas positivas, negativas, de frontera y de integración. |

Los errores se representan mediante objetos estructurados con código, ruta y mensaje. Esto permite mostrar un diagnóstico humano ahora y reutilizar la misma información en logs o CI más adelante.

## 3. Muestras representativas

### Dataset y configuración

Se prueban los ejemplos JSON versionados en `schemas/examples/`: dos deben aceptarse y dos deben rechazarse. Además, las pruebas construyen variantes controladas para demostrar la detección de hashes, IDs, órdenes, cajas y referencias incoherentes. `glossary-mismatch.yaml` aporta un caso negativo de idiomas incompatibles.

### PDF sintético reproducible

`tests/fixtures/representative_pdf.py` genera en una carpeta temporal tres páginas con:

- Título, párrafo y lista con distintos estilos.
- Bloque de código e imagen rasterizada.
- Dos columnas, cabecera, pie y número de página.

El binario no se versiona: se recrea de forma determinista en cada ejecución y se elimina con el directorio temporal de pytest.

### PDF real

`tests/fixtures/pdf-samples.yaml` selecciona ocho páginas físicas del documento de 284 páginas:

| Página física | Caso comprobado |
|---:|---|
| 1 | Portada y texto principal. |
| 2 | Recurso gráfico sin texto extraíble. |
| 19 | Apertura de capítulo y numeración impresa inicial. |
| 22 | Texto acompañado por varias figuras. |
| 31 | Código y hashes. |
| 100 | Definición técnica con estilos jerárquicos. |
| 200 | Lista numerada y elemento gráfico. |
| 284 | Contraportada. |

El manifiesto usa páginas físicas desde 1, igual que el contrato. No confunde esa posición con el número que aparece impreso en el libro.

## 4. Preparar el entorno

Desde la raíz del repositorio en PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

No es obligatorio activar el entorno virtual. Invocar su intérprete directamente evita las restricciones de `ExecutionPolicy` de PowerShell y garantiza qué Python ejecuta el proceso.

## 5. Ejecutar las pruebas

### Batería completa

```powershell
.\.venv\Scripts\python.exe -m pytest --cov=lab_pdf_translator --cov-report=term-missing
```

Resultado de referencia al cerrar la fase 0:

```text
58 passed
TOTAL coverage: 90.98%
```

`pyproject.toml` exige al menos un 90 % de cobertura. La opción `--cov` es necesaria para aplicar ese umbral; por ello está incluida obligatoriamente en la barrera automática. El comando anterior devuelve código `0` solo si no existen fallos y se conserva la cobertura.

### Pruebas rápidas sin PDF

```powershell
.\.venv\Scripts\python.exe -m pytest -m "not integration"
```

Este comando es útil mientras se modifica lógica interna. La batería completa sigue siendo obligatoria antes de cerrar una tarea.

### Informe explícito de cobertura

```powershell
.\.venv\Scripts\python.exe -m pytest --cov=lab_pdf_translator --cov-report=term-missing
```

La columna `Missing` identifica líneas no ejecutadas. El objetivo del umbral es señalar regresiones de prueba, no sustituir la revisión funcional o visual.

## 6. Ejecutar la validación de aceptación

```powershell
.\.venv\Scripts\python.exe scripts\validate_phase0.py
```

La salida correcta tiene esta forma:

```text
PHASE 0 VALIDATION
========================================================================
[PASS] configuration: settings and glossary valid; source=en; target=es
[PASS] schema_definition: JSON Schema Draft 2020-12 definition is valid
[PASS] contract_examples: 2 valid examples accepted; 2 invalid examples rejected
[PASS] pdf_samples: 8 representative pages verified in 284-page PDF
========================================================================
RESULT: PASS
```

El código de salida es `0` con `RESULT: PASS` y `1` con `RESULT: FAIL`. Ante un fallo, el informe añade debajo del control el código, la ruta del dato y el mensaje. Esto permite usar el comando tanto manualmente como en una futura acción de CI.

## 7. Qué valida cada control

- **Configuración:** tipos, versiones, rutas confinadas al proyecto, límites de páginas, idiomas, fases habilitadas y coherencia del glosario.
- **Esquema:** metacontrato Draft 2020-12, formatos y ejemplos positivos y negativos.
- **Semántica:** SHA-256, UUID v5 recalculados, secuencias desde 1, orden de páginas y elementos, cajas válidas y dentro de página, unicidad y referencias de recursos.
- **PDF:** existencia, apertura, número total de páginas, texto mínimo, fragmentos esperados y cantidad mínima de imágenes en cada muestra declarada.

La validación no modifica datasets ni documentos. Recoge todos los problemas razonablemente independientes para evitar ciclos de corrección de un solo error.

## 8. Reglas para ampliar la batería

Toda regla nueva debe incorporar al menos un caso válido y uno inválido. Todo defecto corregido debe conservar una prueba de regresión. Los fixtures binarios grandes no se duplican: se referencian mediante manifiestos o se generan en directorios temporales. Cada nuevo módulo de código debe mantener la fecha de intervención en su bloque de bitácora y comentarios centrados en decisiones, no en repetir instrucciones evidentes.

Antes de integrar un cambio debe pasar `scripts/quality_gate.py`, que reúne la batería completa y `validate_phase0.py`. Si cambia una muestra real, debe revisarse visualmente la página afectada además de actualizar sus expectativas.

La operación unificada y el bootstrap Windows se detallan en [`automated-quality-gate.md`](automated-quality-gate.md).

## 9. Límites actuales

- Aún no se prueba una extracción completa a `data/raw`; se implementará en la fase 1.
- No existen comparaciones visuales píxel a píxel porque todavía no hay renderizador de salida.
- La integración completa necesita el PDF de referencia presente en `input/`; las pruebas unitarias y el PDF sintético siguen siendo independientes.
- La cobertura mide código ejecutado, no calidad lingüística ni fidelidad editorial.

Estos límites son deliberados y evitan declarar como terminadas capacidades que pertenecen a las siguientes fases.
