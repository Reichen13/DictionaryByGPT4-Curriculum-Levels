from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "images" / "social-preview.png"

WIDTH = 1280
HEIGHT = 640

BG_TOP = (245, 238, 223)
BG_BOTTOM = (232, 224, 208)
INK = (29, 41, 35)
MUTED = (88, 102, 94)
ACCENT = (47, 103, 81)
ACCENT_LIGHT = (214, 233, 224)
CARD = (255, 252, 245, 232)
LINE = (214, 204, 186, 170)

EN_FONT = "C:/Windows/Fonts/bahnschrift.ttf"
ZH_FONT = "C:/Windows/Fonts/msyh.ttc"
ZH_FONT_BOLD = "C:/Windows/Fonts/msyhbd.ttc"


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size=size)


def vertical_gradient() -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), BG_TOP)
    draw = ImageDraw.Draw(image)
    for y in range(HEIGHT):
        ratio = y / max(HEIGHT - 1, 1)
        color = tuple(int(BG_TOP[i] * (1 - ratio) + BG_BOTTOM[i] * ratio) for i in range(3))
        draw.line((0, y, WIDTH, y), fill=color)
    return image


def draw_grid(draw: ImageDraw.ImageDraw) -> None:
    step = 48
    for x in range(0, WIDTH, step):
        draw.line((x, 0, x, HEIGHT), fill=(255, 255, 255, 22), width=1)
    for y in range(0, HEIGHT, step):
        draw.line((0, y, WIDTH, y), fill=(255, 255, 255, 18), width=1)


def draw_blob(base: Image.Image, box: tuple[int, int, int, int], fill: tuple[int, int, int, int], blur: int) -> None:
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    draw.ellipse(box, fill=fill)
    layer = layer.filter(ImageFilter.GaussianBlur(blur))
    base.alpha_composite(layer)


def rounded_panel(base: Image.Image, box: tuple[int, int, int, int], radius: int = 30) -> None:
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    draw.rounded_rectangle(box, radius=radius, fill=CARD, outline=LINE, width=2)
    shadow = layer.filter(ImageFilter.GaussianBlur(10))
    base.alpha_composite(Image.new("RGBA", base.size, (0, 0, 0, 0)))
    base.alpha_composite(shadow, (0, 8))
    base.alpha_composite(layer)


def draw_stage_card(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    size: tuple[int, int],
    title: str,
    subtitle: str,
    fill: tuple[int, int, int],
) -> None:
    x, y = xy
    w, h = size
    draw.rounded_rectangle((x, y, x + w, y + h), radius=24, fill=fill, outline=(255, 255, 255, 180), width=2)
    draw.text((x + 22, y + 16), title, fill=(255, 255, 255), font=font(ZH_FONT_BOLD, 26))
    draw.text((x + 22, y + 54), subtitle, fill=(247, 250, 248), font=font(EN_FONT, 20))


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    base = vertical_gradient().convert("RGBA")
    draw_blob(base, (-80, -120, 400, 280), (73, 138, 112, 92), 38)
    draw_blob(base, (840, -40, 1360, 320), (225, 160, 84, 58), 44)
    draw_blob(base, (880, 380, 1320, 760), (47, 103, 81, 68), 42)

    draw = ImageDraw.Draw(base, "RGBA")
    draw_grid(draw)

    rounded_panel(base, (56, 54, 712, 584))
    rounded_panel(base, (760, 84, 1218, 556))

    draw = ImageDraw.Draw(base, "RGBA")

    draw.text((96, 96), "DictionaryByGPT4", fill=ACCENT, font=font(EN_FONT, 44))
    draw.text((96, 152), "正式课标分级版", fill=INK, font=font(ZH_FONT_BOLD, 64))
    draw.text((96, 232), "Curriculum-based vocabulary staging for Chinese learners", fill=MUTED, font=font(EN_FONT, 25))

    desc_lines = [
        "小学 / 初中 / 高中采用",
        "正式课标附录词表分级",
        "四六级与更高阶保留公开词表补充分层",
    ]
    for idx, line in enumerate(desc_lines):
        draw.text((96, 286 + idx * 34), line, fill=INK, font=font(ZH_FONT, 22))

    draw.rounded_rectangle((96, 366, 332, 414), radius=24, fill=ACCENT_LIGHT)
    draw.text((118, 378), "Open-source rearrangement", fill=ACCENT, font=font(EN_FONT, 22))

    draw.rounded_rectangle((346, 366, 596, 414), radius=24, fill=(236, 228, 211))
    draw.text((368, 378), "Official curriculum rules", fill=INK, font=font(EN_FONT, 22))

    draw.text((96, 474), "Based on CeeLog/DictionaryByGPT4", fill=MUTED, font=font(EN_FONT, 24))
    draw.text((96, 516), "Maintained by Reichen13", fill=INK, font=font(EN_FONT, 26))

    stage_colors = [
        (68, 128, 98),
        (78, 140, 111),
        (88, 152, 125),
        (95, 114, 165),
        (111, 96, 160),
        (126, 84, 143),
    ]
    stage_labels = [
        ("小学", "PRIMARY"),
        ("初中", "JUNIOR"),
        ("高中", "SENIOR"),
        ("四级", "CET-4"),
        ("六级", "CET-6"),
        ("更高阶", "ADVANCED"),
    ]
    positions = [
        (808, 122),
        (878, 178),
        (948, 234),
        (1018, 290),
        (948, 346),
        (878, 402),
    ]

    for (title, subtitle), pos, fill in zip(stage_labels, positions, stage_colors, strict=True):
        draw_stage_card(draw, pos, (228, 78), title, subtitle, fill)

    draw.rounded_rectangle((824, 484, 1152, 534), radius=22, fill=(255, 255, 255, 150))
    draw.text((850, 499), "Staged learning order", fill=INK, font=font(EN_FONT, 20))

    base.convert("RGB").save(OUTPUT, quality=95)
    print(f"Generated {OUTPUT}")


if __name__ == "__main__":
    main()
