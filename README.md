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