# lab-pdf-translator

pdf-translator/
│
├── input/
│   └── mastering_blockchain.pdf
│
├── data/
│   ├── raw/
│   │   └── document.json
│   │
│   ├── curated/
│   │   └── blocks.jsonl
│   │
│   └── translated/
│       └── blocks_es.jsonl
│
├── assets/
│   └── images/
│
├── config/
│   ├── glossary.yaml
│   └── settings.yaml
│
├── src/
│   ├── models/
│   │   └── document.py
│   │
│   ├── extraction/
│   │   └── pdf_extractor.py
│   │
│   ├── processing/
│   │   ├── cleaner.py
│   │   ├── classifier.py
│   │   └── paragraph_merger.py
│   │
│   ├── translation/
│   │   ├── base.py
│   │   └── deepl.py
│   │
│   └── rendering/
│       └── pdf_renderer.py
│
├── scripts/
│   ├── extract.py
│   ├── transform.py
│   ├── translate.py
│   └── render.py
│
├── output/
│   └── mastering_blockchain_es.pdf
│
├── tests/
│
├── requirements.txt
└── README.md




El primer objetivo sería solamente:

Convertir las 284 páginas del PDF en una representación JSON estructurada sin perder la información necesaria para reconstruir posteriormente el documento.


☐ Detecta las 284 páginas
☐ Extrae texto
☐ Extrae bbox
☐ Extrae fuentes/tamaño
☐ Identifica imágenes
☐ Genera IDs únicos
☐ Guarda JSON válido
☐ No modifica contenido
☐ Puede ejecutarse varias veces

primer objetivo:

Página 19
Página 22
Página 31
Página con código
Página con imagen
Página con listas

