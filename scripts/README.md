# Scripts

Esta carpeta contendrá puntos de entrada sencillos para ejecutar cada fase desde la terminal.

Los scripts previstos son:

- `extract.py`: documento de entrada a dataset `raw`.
- `transform.py`: dataset `raw` a `curated`.
- `translate.py`: dataset `curated` a `translated`.
- `render.py`: dataset `translated` a PDF o DOCX.
- `run_pipeline.py`: coordinación opcional del flujo completo.

Los scripts solo interpretarán argumentos y delegarán la lógica a `src/lab_pdf_translator/`. No contendrán reglas de negocio para evitar duplicaciones y facilitar las pruebas.
