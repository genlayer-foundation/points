#!/usr/bin/env python3
from __future__ import annotations

import math
import subprocess
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "public" / "assets"
OG_DIR = ASSETS / "og"
BACKDROPS = OG_DIR / "backdrops"
FONTS = ROOT / "public" / "fonts"

WIDTH = 1200
HEIGHT = 630

THEMES = {
    "dark": {
        "title": (255, 255, 255, 255),
        "body": (230, 230, 230, 225),
        "muted": (255, 255, 255, 178),
        "accent": (255, 255, 255, 255),
        "logo": "white",
    },
    "light": {
        "title": (13, 13, 15, 255),
        "body": (37, 37, 42, 230),
        "muted": (28, 28, 32, 170),
        "accent": (13, 13, 15, 255),
        "logo": "black",
    },
}

ROLE_HEXAGONS = {
    "genlayer": ASSETS / "icons" / "hexagon-genlayer.svg",
    "builder": ASSETS / "icons" / "hexagon-builder.svg",
    "validator": ASSETS / "icons" / "hexagon-validator.svg",
    "community": ASSETS / "icons" / "hexagon-community.svg",
}

ROLE_INNER_ICONS = {
    "genlayer": ASSETS / "icons" / "gl-symbol-white.svg",
    "builder": ASSETS / "icons" / "terminal-fill-white.svg",
    "validator": ASSETS / "icons" / "shield-white.svg",
    "community": ASSETS / "icons" / "group-white.svg",
}

LOGO_SYMBOLS = {
    "white": ASSETS / "icons" / "gl-symbol-white.svg",
    "black": ASSETS / "gl-symbol-black.svg",
}


CARDS = [
    {
        "file": "portal",
        "backdrop": "portal",
        "theme": "dark",
        "eyebrow": "GenLayer Portal",
        "title": "GenLayer Portal",
        "description": "Track contributions, points, validators, builders, community activity, events, and ecosystem programs.",
        "roles": ["genlayer", "builder", "validator", "community"],
    },
    {
        "file": "how-it-works",
        "backdrop": "points",
        "theme": "light",
        "eyebrow": "How It Works",
        "title": "How GenLayer Portal Works",
        "description": "Connect builders, validators, and community contributors through points, missions, referrals, and ecosystem programs.",
        "roles": ["builder", "validator", "community"],
    },
    {
        "file": "referral-program",
        "backdrop": "points",
        "theme": "light",
        "eyebrow": "Referral Program",
        "title": "GenLayer Referral Program",
        "description": "Earn 10% of eligible builder and validator contribution points forever, with no cap.",
        "roles": ["builder", "validator"],
    },
    {
        "file": "hackathon",
        "backdrop": "hackathon",
        "theme": "dark",
        "eyebrow": "Testnet Bradbury",
        "title": "Testnet Bradbury Hackathon",
        "description": "Compete for prizes and Builder Points by shipping AI-native applications and Intelligent Contracts.",
        "roles": ["builder"],
    },
    {
        "file": "hackathon-winners",
        "backdrop": "hackathon-winners",
        "theme": "dark",
        "eyebrow": "Testnet Bradbury",
        "title": "Testnet Bradbury Winners",
        "description": "Meet the winning projects from two weeks of AI-native building across the GenLayer ecosystem.",
        "roles": ["builder"],
    },
    {
        "file": "genesis",
        "backdrop": "genesis",
        "theme": "dark",
        "eyebrow": "GenLayer Genesis",
        "title": "GenLayer Genesis",
        "description": "Essays on AI-mediated judgment and infrastructure for commerce between humans and machines.",
        "roles": ["genlayer"],
    },
    {
        "file": "genesis-manifesto",
        "backdrop": "genesis",
        "theme": "dark",
        "eyebrow": "GenLayer Genesis",
        "title": "GenLayer Manifesto",
        "description": "Trust, decentralization, and why AI-native adjudication needs open infrastructure.",
        "roles": ["genlayer"],
    },
    {
        "file": "genesis-whitepaper",
        "backdrop": "genesis",
        "theme": "dark",
        "eyebrow": "GenLayer Genesis",
        "title": "GenLayer Whitepaper",
        "description": "Technical framing for AI-powered smart contracts, subjective consensus, and decentralized judgment.",
        "roles": ["genlayer"],
    },
    {
        "file": "genesis-compass",
        "backdrop": "genesis",
        "theme": "dark",
        "eyebrow": "GenLayer Genesis",
        "title": "GenLayer Compass",
        "description": "A strategic map of agentic commerce and the trust infrastructure for AI-native coordination.",
        "roles": ["genlayer"],
    },
    {
        "file": "gen-tv",
        "backdrop": "media",
        "theme": "dark",
        "eyebrow": "GenTV",
        "title": "GenTV",
        "description": "Watch GenLayer streams, ecosystem conversations, builder sessions, and community programming.",
        "roles": [],
    },
    {
        "file": "gen-news",
        "backdrop": "media",
        "theme": "dark",
        "eyebrow": "GenLayer News",
        "title": "GenLayer News",
        "description": "Follow ecosystem news, builder highlights, community announcements, and GenLayer updates.",
        "roles": [],
    },
    {
        "file": "ecosystem-partners",
        "backdrop": "ecosystem",
        "theme": "light",
        "eyebrow": "Ecosystem",
        "title": "GenLayer Ecosystem Partners",
        "description": "Discover projects, validators, partners, and builders contributing to the GenLayer ecosystem.",
        "roles": ["builder", "validator", "community"],
    },
    {
        "file": "builders-resources",
        "backdrop": "points",
        "theme": "light",
        "eyebrow": "Builder Resources",
        "title": "GenLayer Builder Resources",
        "description": "Find tools, references, examples, and Intelligent Contract resources for building on GenLayer.",
        "roles": ["builder"],
    },
    {
        "file": "builder-project",
        "backdrop": "ecosystem",
        "theme": "light",
        "eyebrow": "Builder Project",
        "title": "GenLayer Builder Project",
        "description": "Explore builder project overviews, milestones, media, and accepted contributions in the ecosystem.",
        "roles": ["builder"],
    },
    {
        "file": "community-poaps",
        "backdrop": "ecosystem",
        "theme": "light",
        "eyebrow": "Community",
        "title": "GenLayer Community POAPs",
        "description": "Explore POAPs, badges, and collectible moments from events, campaigns, and ecosystem participation.",
        "roles": ["community"],
    },
    {
        "file": "participants",
        "backdrop": "ecosystem",
        "theme": "light",
        "eyebrow": "Participants",
        "title": "GenLayer Participants",
        "description": "Browse validator operators and ecosystem contributors across the GenLayer Portal.",
        "roles": ["builder", "validator", "community"],
    },
    {
        "file": "validators-participants",
        "backdrop": "validators",
        "theme": "light",
        "eyebrow": "Validators",
        "title": "GenLayer Validator Participants",
        "description": "Browse operators contributing to GenLayer testnets and network reliability.",
        "roles": ["validator"],
    },
    {
        "file": "validators-waitlist",
        "backdrop": "validators",
        "theme": "light",
        "eyebrow": "Validators",
        "title": "Join the Validator Waitlist",
        "description": "Apply to contribute to testnet operations and prepare for network reliability work.",
        "roles": ["validator"],
    },
    {
        "file": "validators-wall-of-shame",
        "backdrop": "validators",
        "theme": "light",
        "eyebrow": "Validators",
        "title": "Validator Reliability Signals",
        "description": "Track uptime issues and reliability signals from GenLayer testnet participation.",
        "roles": ["validator"],
    },
    {
        "file": "terms-of-use",
        "backdrop": "portal",
        "theme": "dark",
        "eyebrow": "Legal",
        "title": "GenLayer Portal Terms of Use",
        "description": "Review the terms that govern access to and use of GenLayer Portal and related services.",
        "roles": [],
    },
    {
        "file": "privacy-policy",
        "backdrop": "portal",
        "theme": "dark",
        "eyebrow": "Legal",
        "title": "GenLayer Portal Privacy Policy",
        "description": "Review how GenLayer Portal handles privacy, personal information, and related data practices.",
        "roles": [],
    },
]


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / path), size)


TITLE_FONT_PATH = "F37Lineca-VF.ttf"
BODY_FONT_PATH = "Geist-VariableFont_wght.woff2"


def cover(im: Image.Image, size: tuple[int, int]) -> Image.Image:
    target_w, target_h = size
    ratio = max(target_w / im.width, target_h / im.height)
    resized = im.resize((math.ceil(im.width * ratio), math.ceil(im.height * ratio)), Image.LANCZOS)
    left = (resized.width - target_w) // 2
    top = (resized.height - target_h) // 2
    return resized.crop((left, top, left + target_w, top + target_h))


def render_svg(svg_path: Path, width: int, height: int | None = None) -> Image.Image:
    command = ["rsvg-convert", "-w", str(width)]
    if height is not None:
        command.extend(["-h", str(height)])
    command.append(str(svg_path))
    png = subprocess.check_output(command)
    return Image.open(BytesIO(png)).convert("RGBA")


def alpha_composite(base: Image.Image, overlay: Image.Image, xy: tuple[int, int]) -> None:
    base.alpha_composite(overlay, xy)


def add_readability_overlay(base: Image.Image, theme: str) -> None:
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    pix = overlay.load()
    for x in range(WIDTH):
        if theme == "dark":
            alpha = int(max(0, 230 * (1 - x / 780)))
            color = (0, 0, 0, alpha)
        else:
            alpha = int(max(0, 248 * (1 - x / 780)))
            color = (255, 255, 255, alpha)
        for y in range(HEIGHT):
            pix[x, y] = color
    base.alpha_composite(overlay)

    vignette = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(vignette)
    if theme == "dark":
        draw.rectangle((0, 0, WIDTH, HEIGHT), outline=(0, 0, 0, 90), width=2)
    else:
        draw.rectangle((0, 0, WIDTH, HEIGHT), outline=(10, 10, 10, 18), width=2)
    base.alpha_composite(vignette)


def wrap_text(text: str, draw: ImageDraw.ImageDraw, text_font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        width = draw.textbbox((0, 0), candidate, font=text_font)[2]
        if width <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def fit_title(draw: ImageDraw.ImageDraw, text: str, max_width: int, max_lines: int) -> tuple[ImageFont.FreeTypeFont, list[str]]:
    for size in range(84, 55, -2):
        title_font = font(TITLE_FONT_PATH, size)
        lines = wrap_text(text, draw, title_font, max_width)
        if len(lines) <= max_lines:
            return title_font, lines
    title_font = font(TITLE_FONT_PATH, 54)
    return title_font, wrap_text(text, draw, title_font, max_width)


def draw_multiline(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    lines: list[str],
    text_font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int, int],
    line_gap: int,
) -> int:
    x, y = xy
    for line in lines:
        draw.text((x, y), line, font=text_font, fill=fill)
        bbox = draw.textbbox((x, y), line, font=text_font)
        y += bbox[3] - bbox[1] + line_gap
    return y


def draw_brand(base: Image.Image, theme: str) -> None:
    palette = THEMES[theme]
    logo_color = palette["logo"]
    symbol = render_svg(LOGO_SYMBOLS[logo_color], 42)
    x = 72
    y = 58
    alpha_composite(base, symbol, (x, y))

    draw = ImageDraw.Draw(base)
    brand_font = font(BODY_FONT_PATH, 36)
    draw.text((x + 54, y + 1), "GenLayer", font=brand_font, fill=palette["accent"])


def draw_role_hexes(base: Image.Image, roles: list[str]) -> None:
    if not roles:
        return

    size = 58
    gap = 12
    x = 72
    y = HEIGHT - 110
    for role in roles[:4]:
        icon_path = ROLE_HEXAGONS.get(role)
        if not icon_path:
            continue
        icon = render_svg(icon_path, size)
        alpha_composite(base, icon, (x, y))
        inner_path = ROLE_INNER_ICONS.get(role)
        if inner_path:
            inner = render_svg(inner_path, round(size * 0.52))
            alpha_composite(
                base,
                inner,
                (x + (size - inner.width) // 2, y + (size - inner.height) // 2),
            )
        x += size + gap


def render_card(card: dict[str, object]) -> None:
    theme = str(card["theme"])
    palette = THEMES[theme]
    backdrop = Image.open(BACKDROPS / f"{card['backdrop']}.png").convert("RGBA")
    base = cover(backdrop, (WIDTH, HEIGHT))
    base = base.filter(ImageFilter.UnsharpMask(radius=1, percent=105, threshold=3))
    add_readability_overlay(base, theme)

    draw_brand(base, theme)
    draw = ImageDraw.Draw(base)

    eyebrow_font = font(BODY_FONT_PATH, 24)
    draw.text((72, 150), str(card["eyebrow"]).upper(), font=eyebrow_font, fill=palette["muted"])

    title_font, title_lines = fit_title(draw, str(card["title"]), 690, 3)
    title_bottom = draw_multiline(draw, (72, 190), title_lines, title_font, palette["title"], 6)

    body_font = font(BODY_FONT_PATH, 27)
    body_lines = wrap_text(str(card["description"]), draw, body_font, 690)
    draw_multiline(draw, (72, title_bottom + 18), body_lines[:3], body_font, palette["body"], 8)

    draw_role_hexes(base, list(card.get("roles", [])))

    output = OG_DIR / f"{card['file']}.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    base.convert("RGB").save(output, "PNG", optimize=True)


def main() -> None:
    for card in CARDS:
        render_card(card)
    print(f"Rendered {len(CARDS)} OG images to {OG_DIR}")


if __name__ == "__main__":
    main()
