"""Draws a SYNTHETIC vaccination card (no real person's data) for OCR testing.

Run:  python tests/samples/make_sample_card.py
Output: tests/samples/sample_card.png
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).with_name("sample_card.png")
ROWS = [
    ("Vaccine", "Dose", "Date given"),
    ("BCG", "", "14/03/2020"),
    ("Hepatitis B", "1", "14/03/2020"),
    ("OPV", "1", "25/04/2020"),
    ("OPV", "2", "06/06/2020"),
    ("Pentavalent", "1", "25/04/2020"),
    ("MR", "1", "20/12/2020"),
]


def load_font(size: int) -> ImageFont.FreeTypeFont:
    for name in ("DejaVuSans.ttf", "arial.ttf", "Arial.ttf", "LiberationSans-Regular.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size)


def main() -> None:
    img = Image.new("RGB", (1100, 640), "white")
    d = ImageDraw.Draw(img)
    d.text((40, 24), "IMMUNIZATION CARD (SAMPLE)", fill="black", font=load_font(34))
    y = 100
    for i, (vaccine, dose, when) in enumerate(ROWS):
        font = load_font(30)
        d.rectangle([30, y - 8, 1070, y + 56], outline="black", width=2)
        d.text((50, y), vaccine, fill="black", font=font)
        d.text((520, y), dose, fill="black", font=font)
        d.text((680, y), when, fill="black", font=font)
        y += 72
    img.save(OUT)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
