"""Render `public/og.png`, the card every link preview shows.

Run when the headline, the description, or the brand ramp changes:

    uv run --with pillow --with numpy --with fonttools --with brotli \
        python scripts/generate-og.py

The output is committed rather than built. Next can render this card from JSX
via a metadata image route, but a static export emits that route as an
extensionless file, and GitHub Pages then serves it as
`application/octet-stream` — which every link-preview crawler rejects. A plain
`.png` under `public/` gets the right content type from any host.

Deliberately NOT wired into `npm run build`: the extra Python dependencies buy
nothing on a card that changes once a year.
"""

from __future__ import annotations

import io
from pathlib import Path

import numpy as np
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from PIL import Image, ImageDraw, ImageFont

# Steps of the brand ramp in `app/global.css`, converted to sRGB. Kept next to
# the drawing code because Pillow parses neither oklch nor CSS variables.
INK = (10, 12, 7)
GLOW = (33, 39, 13)
PAPER = (244, 246, 241)
LIME = (206, 242, 75)
MARK_GROUND = (5, 31, 32)
MUTED = (151, 153, 147)

SIZE = (1200, 630)
MARGIN = 80
HEADLINE = 'The protocol owns control. The model owns content.'
DESCRIPTION = 'Declarative multiparty session protocols for AI agents.'

DOCS = Path(__file__).resolve().parent.parent


def geist(weight: int, size: int) -> ImageFont.FreeTypeFont:
    """A static instance of the variable Geist at one weight, as a PIL font."""
    font = TTFont(DOCS / 'public/fonts/Geist-Variable.woff2')
    font.flavor = None
    instancer.instantiateVariableFont(font, {'wght': weight}, inplace=True)
    buffer = io.BytesIO()
    font.save(buffer)
    buffer.seek(0)
    return ImageFont.truetype(buffer, size)


def ground() -> Image.Image:
    """The ink field, lifted toward the lower right.

    Stands in for the landing page's shader: the same ramp, reduced to the one
    gradient a still card can carry without pretending to be the animation.
    """
    y, x = np.mgrid[0 : SIZE[1], 0 : SIZE[0]]
    distance = np.hypot((x - SIZE[0] * 0.88) / 1000, (y - SIZE[1] * 1.08) / 620)
    weight = np.clip(1.0 - distance, 0.0, 1.0)[..., None] ** 1.6
    field = np.array(INK) + (np.array(GLOW) - np.array(INK)) * weight
    return Image.fromarray(field.astype('uint8'), 'RGB')


def wrap(text: str, font: ImageFont.FreeTypeFont, width: int) -> list[str]:
    """Greedy line breaking; the headline is short enough to need nothing more."""
    lines: list[str] = ['']
    for word in text.split():
        candidate = f'{lines[-1]} {word}'.strip()
        if font.getlength(candidate) <= width or not lines[-1]:
            lines[-1] = candidate
        else:
            lines.append(word)
    return lines


def main() -> None:
    card = ground()
    draw = ImageDraw.Draw(card)

    # the mark, matching app/icon.svg:
    draw.rounded_rectangle(
        (MARGIN, MARGIN, MARGIN + 64, MARGIN + 64), radius=20, fill=MARK_GROUND
    )
    draw.text(
        (MARGIN + 32, MARGIN + 30),
        '&',
        font=geist(600, 44),
        fill=LIME,
        anchor='mm',
    )
    draw.text(
        (MARGIN + 84, MARGIN + 32),
        'agentsparty',
        font=geist(600, 30),
        fill=PAPER,
        anchor='lm',
    )

    # the headline, set to the same measure as the hero's:
    headline = geist(600, 68)
    lines = wrap(HEADLINE, headline, 900)
    baseline = 300
    for index, line in enumerate(lines):
        draw.text((MARGIN, baseline + index * 74), line, font=headline, fill=PAPER)

    # the rule and the description:
    footer = SIZE[1] - MARGIN - 14
    draw.rectangle((MARGIN, footer, MARGIN + 56, footer + 3), fill=LIME)
    draw.text(
        (MARGIN + 80, footer + 2),
        DESCRIPTION,
        font=geist(400, 26),
        fill=MUTED,
        anchor='lm',
    )

    out = DOCS / 'public/og.png'
    card.save(out, optimize=True)
    print(f'{out.relative_to(DOCS)} {out.stat().st_size} bytes')


if __name__ == '__main__':
    main()
