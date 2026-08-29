# Barrera automática de calidad

> Bitácora: 30/08/2026 — definida e implementada la puerta única de aprobación técnica.

## 1. Qué problema resuelve

Antes existían comandos independientes para pruebas, cobertura, dependencias y validación del contrato. Cada uno era correcto, pero una persona podía ejecutar solo una parte y concluir por error que la entrega estaba aprobada.

La barrera automática convierte todos los controles obligatorios en una sola decisión:

```text
Dependencias coherentes
        +
Pruebas completas y cobertura >= 90 %
        +
Configuración, contrato, ejemplos y PDF válidos
        =
RESULT: PASS y código de salida 0
```

Si falla una sola condición, el resultado completo es `FAIL` y el proceso devuelve un código distinto de cero.

## 2. Componentes

| Archivo | Función |
|---|---|
| `src/lab_pdf_translator/validation/quality_gate.py` | Define las etapas, ejecuta los comandos y agrega la decisión. |
| `scripts/quality_gate.py` | Interfaz multiplataforma para un entorno que ya tiene dependencias. |
| `scripts/run_quality_gate.cmd` | Bootstrap Windows: crea y activa `.venv`, instala dependencias y lanza la barrera. |
| `scripts/validate_phase0.py` | Validación específica de configuración, esquema, ejemplos y PDF, reutilizada por la barrera. |
| `tests/test_quality_gate.py` | Prueba que ninguna etapa se omita y que cualquier fallo cierre la puerta. |

La lógica reside en `src/`; los scripts solo preparan el contexto y presentan el resultado.

## 3. Etapas y orden

### Etapa 1: dependencias

Ejecuta:

```powershell
python -m pip check
```

Detecta requisitos incompatibles o rotos dentro del entorno efectivo.

### Etapa 2: pruebas y cobertura

Ejecuta explícitamente:

```powershell
python -m pytest --cov=lab_pdf_translator --cov-report=term-missing
```

`pyproject.toml` fija `fail_under = 90`. La opción `--cov` se incluye dentro de la barrera y no depende de que el usuario la recuerde. Un test fallido o cobertura inferior al 90 % devuelve error.

### Etapa 3: aceptación de fase 0

Reutiliza `run_phase0_validation` y comprueba:

- Configuración y glosario.
- Definición JSON Schema Draft 2020-12.
- Dos ejemplos válidos y dos inválidos.
- Ocho páginas representativas del PDF esperado.

## 4. Ejecución recomendada en Windows

Desde PowerShell o CMD situado en la raíz del repositorio:

```powershell
.\scripts\run_quality_gate.cmd
```

El lanzador:

1. Cambia de forma segura a la raíz del repositorio.
2. Busca `.venv\Scripts\python.exe`.
3. Si no existe, verifica que el comando `python` sea de la serie 3.14 y crea `.venv` con ese intérprete.
4. Activa el entorno con `activate.bat`, que no depende de `ExecutionPolicy` de PowerShell.
5. Instala o verifica `requirements-dev.txt`.
6. Ejecuta `scripts/quality_gate.py`.
7. Desactiva el entorno dentro del proceso del lanzador.
8. Propaga el código real de aprobación o fallo.

La activación solo vive durante el proceso `.cmd`; al terminar no altera permanentemente la sesión del usuario.

## 5. Ejecución rápida con entorno preparado

Si `.venv` ya contiene las dependencias:

```powershell
.\.venv\Scripts\python.exe scripts\quality_gate.py
```

Este es también el comando recomendado para una futura integración continua después de instalar `requirements-dev.txt`.

## 6. Salida esperada

Pytest muestra primero el detalle de pruebas y cobertura. Después aparece el resumen estable:

```text
========================================================================
[PASS] dependencies: installed dependencies are coherent
[PASS] tests_and_coverage: pytest passed and coverage reached the configured threshold
[PASS] phase0_acceptance: 4 contract and PDF checks passed
========================================================================
RESULT: PASS
```

En PowerShell se confirma el código inmediatamente después:

```powershell
$LASTEXITCODE
```

Debe devolver `0`.

## 7. Comportamiento ante fallos

| Resultado | Significado | Acción |
|---|---|---|
| `dependencies: FAIL` | Entorno incoherente. | Reinstalar desde `requirements-dev.txt` y revisar conflictos. |
| `tests_and_coverage: FAIL` | Existe un test fallido o cobertura inferior al 90 %. | Revisar el informe de pytest; no se aprueba el cambio. |
| `phase0_acceptance: FAIL` | Contrato, configuración, ejemplos o PDF incumplen expectativas. | Ejecutar `validate_phase0.py` para el detalle específico. |
| `RESULT: FAIL` | Al menos una etapa falló. | Mantener la tarea en desarrollo o review. |

La barrera ejecuta todas las etapas razonablemente posibles aunque una falle, de modo que el desarrollador recibe un diagnóstico completo en una sola ejecución.

## 8. Uso futuro en CI

Una acción de integración continua deberá:

1. Obtener el repositorio en un entorno limpio.
2. Instalar CPython 3.14.
3. Crear un entorno o instalar `requirements-dev.txt`.
4. Ejecutar `python scripts/quality_gate.py`.
5. Bloquear el merge si el código no es `0`.

La CI no debe copiar las reglas en YAML mediante comandos diferentes. Debe invocar el mismo script local para evitar que el portátil y el servidor tengan definiciones distintas de “aprobado”.

Si el PDF privado deja de estar disponible en CI, primero debe completarse la estrategia pública descrita en [`test-document-governance.md`](test-document-governance.md).

## 9. Criterio de aprobación

El Team Leader puede aceptar técnicamente una entrega cuando:

- El bootstrap termina correctamente desde un entorno compatible.
- Las tres etapas aparecen como `[PASS]`.
- La cobertura alcanza el umbral configurado.
- `RESULT: PASS` es la última decisión de la barrera.
- El código de salida es `0`.
- No se han modificado entradas, configuración o ejemplos como efecto lateral.

La aprobación técnica no sustituye la aprobación de licencia y procedencia de las muestras documentales.
