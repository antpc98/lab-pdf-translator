"""Constructor de un PDF pequeño con casos de maquetación controlados.

Bitácora:
    2026-08-30 - Muestra sintética inicial para pruebas de integración PDF.

El PDF se genera en el directorio temporal de pytest; no es un artefacto de producto
ni se versiona. Su contenido estable permite detectar regresiones en las librerías.
"""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen.canvas import Canvas


def build_representative_pdf(output_path: Path) -> Path:
    """Crea tres páginas con texto, lista, código, imagen y dos columnas."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    width, height = A4
    canvas = Canvas(str(output_path), pagesize=A4, pageCompression=1)
    canvas.setTitle("Phase 0 representative fixture")

    # Página 1: jerarquía tipográfica y lista.
    canvas.setFont("Helvetica-Bold", 22)
    canvas.drawString(56, height - 72, "Representative document")
    canvas.setFont("Helvetica", 11)
    canvas.drawString(56, height - 102, "Paragraph with deterministic text extraction.")
    for index, item in enumerate(("First governed item", "Second governed item"), start=1):
        canvas.drawString(72, height - 130 - (index * 18), f"{index}. {item}")
    _draw_footer(canvas, 1, 3)
    canvas.showPage()

    # Página 2: bloque monoespaciado e imagen raster.
    canvas.setFont("Helvetica-Bold", 16)
    canvas.drawString(56, height - 72, "Code and image")
    canvas.setFillColor(HexColor("#F2F4F7"))
    canvas.rect(56, height - 190, 260, 80, fill=1, stroke=0)
    canvas.setFillColor(HexColor("#111827"))
    canvas.setFont("Courier", 10)
    canvas.drawString(68, height - 135, 'digest = sha256(b"phase-0")')
    canvas.drawString(68, height - 155, "assert len(digest.hexdigest()) == 64")
    canvas.drawImage(_sample_image(), 340, height - 210, width=150, height=110)
    _draw_footer(canvas, 2, 3)
    canvas.showPage()

    # Página 3: dos columnas para validar geometría y orden bruto.
    canvas.setFont("Helvetica-Bold", 16)
    canvas.drawString(56, height - 72, "Two-column layout")
    canvas.setFont("Helvetica", 10)
    for row in range(6):
        canvas.drawString(56, height - 105 - row * 16, f"Left column line {row + 1}")
        canvas.drawString(310, height - 105 - row * 16, f"Right column line {row + 1}")
    _draw_footer(canvas, 3, 3)
    canvas.save()
    return output_path


def _sample_image() -> ImageReader:
    image = Image.new("RGB", (300, 220), "#DDEAFE")
    draw = ImageDraw.Draw(image)
    draw.rectangle((20, 20, 280, 200), outline="#1D4ED8", width=6)
    draw.line((40, 170, 120, 80, 190, 135, 260, 45), fill="#2563EB", width=8)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return ImageReader(buffer)


def _draw_footer(canvas: Canvas, page_number: int, page_count: int) -> None:
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(HexColor("#4B5563"))
    canvas.drawCentredString(A4[0] / 2, 28, f"Page {page_number} of {page_count}")
    canvas.setFillColor(HexColor("#000000"))
