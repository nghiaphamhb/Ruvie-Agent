from __future__ import annotations

import base64
import io
import shutil
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = ROOT / "static" / "static"
BACKUP_DIR = ROOT / "static" / "static-logo-backup-before-ruvie" / "refresh-20260704"

LIGHT_SOURCE = Path(r"E:\Desktop\GitHub Repository\ruvie-asesst-old\light-mode.png")
DARK_SOURCE = Path(r"E:\Desktop\GitHub Repository\ruvie-asesst-old\dark-mode.png")
DARK_BACKGROUND = (15, 23, 42, 255)
BACKGROUND_TOLERANCE = 30

BRAND_FILES = [
    "apple-touch-icon.png",
    "favicon-96x96.png",
    "favicon-dark.png",
    "favicon.ico",
    "favicon.png",
    "favicon.svg",
    "logo.png",
    "splash-dark.png",
    "splash.png",
    "web-app-manifest-192x192.png",
    "web-app-manifest-512x512.png",
]


def backup_existing_assets() -> None:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    if any(BACKUP_DIR.iterdir()):
        return
    for filename in BRAND_FILES:
        source = STATIC_DIR / filename
        if source.exists():
            shutil.copy2(source, BACKUP_DIR / filename)


def resize_square(image: Image.Image, size: int) -> Image.Image:
    return image.resize((size, size), Image.Resampling.LANCZOS)


def make_icon_canvas(source: Image.Image) -> Image.Image:
    width, height = source.size
    crop_box = (
        int(width * 0.22),
        int(height * 0.18),
        int(width * 0.78),
        int(height * 0.60),
    )
    cropped = source.crop(crop_box)

    background = source.getpixel((0, 0))
    canvas = Image.new("RGBA", (512, 512), background)

    max_width = 430
    max_height = 360
    ratio = min(max_width / cropped.width, max_height / cropped.height)
    resized = cropped.resize(
        (int(cropped.width * ratio), int(cropped.height * ratio)),
        Image.Resampling.LANCZOS,
    )

    x = (canvas.width - resized.width) // 2
    y = (canvas.height - resized.height) // 2
    canvas.paste(resized, (x, y))
    return canvas


def recolor_background(
    source: Image.Image,
    target_color: tuple[int, int, int, int],
    reference_color: tuple[int, int, int, int] | None = None,
    tolerance: int = BACKGROUND_TOLERANCE,
) -> Image.Image:
    image = source.convert("RGBA")
    reference = reference_color or image.getpixel((0, 0))
    ref_r, ref_g, ref_b, _ = reference

    result = Image.new("RGBA", image.size)
    src_pixels = image.load()
    dst_pixels = result.load()

    for y in range(image.height):
        for x in range(image.width):
            r, g, b, a = src_pixels[x, y]
            if a == 0:
                dst_pixels[x, y] = (0, 0, 0, 0)
                continue

            distance = abs(r - ref_r) + abs(g - ref_g) + abs(b - ref_b)
            if distance <= tolerance:
                dst_pixels[x, y] = target_color
            else:
                dst_pixels[x, y] = (r, g, b, a)

    return result


def save_svg_icon(icon: Image.Image, destination: Path) -> None:
    buffer = io.BytesIO()
    icon.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">'
        f'<image href="data:image/png;base64,{encoded}" width="512" height="512"/>'
        "</svg>"
    )
    destination.write_text(svg, encoding="utf-8")


def main() -> None:
    if not LIGHT_SOURCE.exists():
        raise FileNotFoundError(f"Light logo source not found: {LIGHT_SOURCE}")
    if not DARK_SOURCE.exists():
        raise FileNotFoundError(f"Dark logo source not found: {DARK_SOURCE}")

    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    backup_existing_assets()

    light_full = Image.open(LIGHT_SOURCE).convert("RGBA")
    dark_full = Image.open(DARK_SOURCE).convert("RGBA")
    dark_full = recolor_background(dark_full, DARK_BACKGROUND)

    light_icon = make_icon_canvas(light_full)
    dark_icon = make_icon_canvas(dark_full)

    light_full.save(STATIC_DIR / "logo.png")
    light_full.save(STATIC_DIR / "splash.png")
    dark_full.save(STATIC_DIR / "splash-dark.png")

    light_icon.save(STATIC_DIR / "favicon.png")
    dark_icon.save(STATIC_DIR / "favicon-dark.png")
    resize_square(light_icon, 96).save(STATIC_DIR / "favicon-96x96.png")
    resize_square(light_icon, 180).save(STATIC_DIR / "apple-touch-icon.png")
    resize_square(light_icon, 192).save(STATIC_DIR / "web-app-manifest-192x192.png")
    resize_square(light_icon, 512).save(STATIC_DIR / "web-app-manifest-512x512.png")

    light_icon.save(
        STATIC_DIR / "favicon.ico",
        sizes=[(16, 16), (32, 32), (48, 48), (64, 64)],
    )
    save_svg_icon(light_icon, STATIC_DIR / "favicon.svg")


if __name__ == "__main__":
    main()
