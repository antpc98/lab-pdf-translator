# Guía de ejecución de scripts

> Bitácora: 30/08/2026 — añadida la guía operativa y consolidada la barrera única de calidad.

Esta carpeta contiene las interfaces de terminal del proyecto. Los scripts reciben la orden del usuario, llaman a la lógica reutilizable de `src/lab_pdf_translator/` y devuelven un resultado legible junto con un código de salida automatizable.

## 1. Ejecución recomendada

La orden oficial de aprobación en Windows es:

```powershell
.\scripts\run_quality_gate.cmd
```

El lanzador crea `.venv` si falta, verifica Python 3.14, activa el entorno dentro de su proceso, instala `requirements-dev.txt` y ejecuta `quality_gate.py`. Esta barrera exige dependencias coherentes, pruebas, cobertura mínima del 90 % y aceptación completa. La referencia detallada está en [`../docs/automated-quality-gate.md`](../docs/automated-quality-gate.md).

## 2. Validador específico

`validate_phase0.py` realiza la comprobación de aceptación de la fase 0. No modifica el PDF, los datasets ni la configuración.

Comprueba, en este orden:

1. Que `config/settings.yaml` y `config/glossary.yaml` sean válidos y coherentes.
2. Que `schemas/document.schema.json` sea un JSON Schema Draft 2020-12 correcto.
3. Que los dos ejemplos válidos sean aceptados y los dos inválidos sean rechazados.
4. Que el PDF de referencia tenga 284 páginas y cumpla las expectativas de ocho páginas representativas.

## 3. Requisitos previos

Abre PowerShell en la raíz del repositorio, donde están `README.md` y `requirements-dev.txt`:

```powershell
cd C:\Users\AntonioPrieto\GIT\lab-pdf-translator
```

Comprueba que el entorno utiliza la versión esperada:

```powershell
.\.venv\Scripts\python.exe --version
```

La salida esperada es:

```text
Python 3.14.7
```

Si `.venv` aún no existe, créalo e instala las dependencias de desarrollo:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

Se invoca directamente el Python del entorno virtual, por lo que no es necesario ejecutar `Activate.ps1` ni cambiar la política de ejecución de PowerShell.

## 4. Ejecutar solo la validación

Desde la raíz del proyecto:

```powershell
.\.venv\Scripts\python.exe scripts\validate_phase0.py
```

Una ejecución correcta debe imprimir:

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

## 5. Cómo revisar la salida

Revisa estas cinco condiciones:

- Aparecen exactamente cuatro controles.
- Los cuatro comienzan con `[PASS]`.
- Los idiomas efectivos son `source=en` y `target=es`.
- Se aceptan dos ejemplos válidos, se rechazan dos inválidos y se verifican ocho muestras de un PDF de 284 páginas.
- La última línea es `RESULT: PASS`.

Comprueba también el código de salida inmediatamente después de ejecutar el script:

```powershell
$LASTEXITCODE
```

Debe mostrar:

```text
0
```

`RESULT: PASS` y el código `0` significan que la barrera automática está superada. Un `[FAIL]`, `RESULT: FAIL` o un código distinto de `0` impide considerar válida la ejecución.

## 6. Interpretar un fallo

| Control | Qué revisar primero |
|---|---|
| `configuration` | Sintaxis y valores de `config/settings.yaml` y `config/glossary.yaml`; rutas, idiomas y versiones. |
| `schema_definition` | Sintaxis y metacontrato de `schemas/document.schema.json`. |
| `contract_examples` | Ejemplos de `schemas/examples/`, IDs deterministas, geometría, órdenes y referencias. |
| `pdf_samples` | Presencia del PDF en `input/`, total de páginas y expectativas de `tests/fixtures/pdf-samples.yaml`. |

Cuando falla un control, el script añade debajo un diagnóstico parecido a este:

```text
[FAIL] configuration: glossary.target_language must match pipeline.target_language
       AUTOMATION_FAILED at $: glossary.target_language must match pipeline.target_language
```

El texto tras `at` indica la ruta lógica del problema y el resto explica la condición incumplida. Corrige el archivo señalado y vuelve a ejecutar el comando completo. No cambies una expectativa únicamente para ocultar un fallo: confirma antes que el contrato o la muestra realmente deban cambiar.

## 7. Ejecutar todas las pruebas

La validación anterior es el resumen de aceptación. Antes de cerrar cambios de código también debe ejecutarse la batería completa:

```powershell
.\.venv\Scripts\python.exe -m pytest --cov=lab_pdf_translator --cov-report=term-missing
```

En el cierre inicial de la fase 0 la referencia es:

```text
58 passed
Required test coverage of 90.0% reached. Total coverage: 90.98%
```

El número de pruebas podrá crecer, pero nunca debe aparecer `failed` o `error`, y la cobertura total debe mantenerse como mínimo en el 90 %.

## 8. Lista final de conformidad

Antes de dar la revisión por buena confirma:

- [ ] Python informa de la versión `3.14.7`.
- [ ] `pytest` termina sin pruebas fallidas y con cobertura igual o superior al 90 %.
- [ ] Los cuatro controles del script aparecen como `[PASS]`.
- [ ] El resultado final es `RESULT: PASS`.
- [ ] `$LASTEXITCODE` devuelve `0`.
- [ ] No se han generado cambios en `input/`, `schemas/examples/` ni `config/` durante la validación.

La explicación técnica y la estrategia completa de pruebas están en [`../docs/testing-and-validation.md`](../docs/testing-and-validation.md).

## 9. Scripts de fases posteriores

La estructura prevé futuras interfaces como `extract.py`, `transform.py`, `translate.py`, `render.py` y `run_pipeline.py`. Se documentarán aquí cuando su comportamiento exista y tenga pruebas; sus nombres no implican que estén implementados actualmente.

La lógica de negocio seguirá fuera de esta carpeta para evitar duplicaciones y permitir que scripts, pruebas y futuras automatizaciones utilicen exactamente las mismas reglas.
