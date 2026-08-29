# Muestras de prueba

> Bitácora: 30/08/2026 — catálogo representativo implementado y validado visualmente.

Esta carpeta contendrá documentos y datasets pequeños, legales y reproducibles para las pruebas automáticas.

No deben copiarse aquí libros completos. Para el PDF inicial se utilizarán referencias a páginas concretas o muestras mínimas derivadas exclusivamente para validar estructura.

Cobertura disponible:

- Documento mínimo de una página.
- Página vacía.
- Texto con varias fuentes y tamaños.
- Encabezado, pie y numeración.
- Listas y bloques de código.
- Imagen con varias apariciones.
- Página con dos columnas.
- Tabla.
- Documento protegido o parcialmente ilegible.
- JSON válidos e inválidos del contrato.

`pdf-samples.yaml` selecciona ocho páginas físicas del PDF de referencia para cubrir portada, recurso gráfico sin texto extraíble, inicio de capítulo, figuras, código, definición, lista numerada y contraportada. Las páginas físicas se usan deliberadamente para no confundirlas con la numeración impresa.

`representative_pdf.py` genera durante la prueba un PDF original y pequeño de tres páginas. Incluye estilos tipográficos, lista, código, imagen, dos columnas, cabecera y pie; así se prueba la librería sin versionar una copia binaria opaca.

`glossary-mismatch.yaml` es una configuración negativa controlada. Permite demostrar que el validador detecta idiomas incoherentes sin alterar la configuración real del laboratorio.
