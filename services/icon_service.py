"""Generate favicon/PWA icon variants from a source image (SVG or raster)."""

from __future__ import annotations

import base64
import io
import logging
import shutil
import struct
from pathlib import Path

from PIL import Image

logger = logging.getLogger(__name__)

# Output filenames by size
OUTPUT_NAMES: dict[int, str] = {
    16: "favicon-16x16.png",
    32: "favicon-32x32.png",
    48: "icon-48x48.png",
    72: "icon-72x72.png",
    96: "icon-96x96.png",
    128: "icon-128x128.png",
    144: "icon-144x144.png",
    152: "icon-152x152.png",
    167: "icon-167x167.png",
    180: "apple-touch-icon.png",
    192: "icon-192x192.png",
    384: "icon-384x384.png",
    512: "icon-512x512.png",
}

MASKABLE_SIZES = [192, 512]
BG_COLOR = (0x0D, 0x0D, 0x0D, 255)


def _render_svg(svg_path: Path, size: int) -> Image.Image:
    """Render SVG to a PIL Image at the given size."""
    import cairosvg

    png_data = cairosvg.svg2png(
        url=str(svg_path), output_width=size, output_height=size
    )
    return Image.open(io.BytesIO(png_data)).convert("RGBA")


def _render_raster(source: Path, size: int) -> Image.Image:
    """Resize a raster image to the given size."""
    img = Image.open(source).convert("RGBA")
    return img.resize((size, size), Image.LANCZOS)


def _make_maskable(icon: Image.Image, size: int) -> Image.Image:
    """Create maskable variant: 80% icon centered on dark background."""
    canvas = Image.new("RGBA", (size, size), BG_COLOR)
    icon_size = int(size * 0.8)
    scaled = icon.resize((icon_size, icon_size), Image.LANCZOS)
    offset = (size - icon_size) // 2
    canvas.paste(scaled, (offset, offset), scaled)
    return canvas


def _build_ico(images: dict[int, Image.Image], output: Path) -> None:
    """Build a .ico file from 16, 32, and 48 px images."""
    sizes = [16, 32, 48]
    entries = []
    for s in sizes:
        entries.append((s, images[s].convert("RGBA")))

    header = struct.pack("<HHH", 0, 1, len(entries))
    dir_offset = 6 + len(entries) * 16
    dir_entries: list[bytes] = []
    image_datas: list[bytes] = []

    for size, img in entries:
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        png_data = buf.getvalue()
        w = 0 if size >= 256 else size
        h = 0 if size >= 256 else size
        dir_entries.append(
            struct.pack("<BBBBHHII", w, h, 0, 0, 1, 32, len(png_data), dir_offset)
        )
        image_datas.append(png_data)
        dir_offset += len(png_data)

    with open(output, "wb") as f:
        f.write(header)
        for de in dir_entries:
            f.write(de)
        for data in image_datas:
            f.write(data)


def generate_icons(source: Path, output_dir: Path) -> None:
    """Generate all icon variants from *source* into *output_dir*.

    Supports SVG (via cairosvg) and raster images (PNG/JPG/WebP via Pillow).
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    is_svg = source.suffix.lower() == ".svg"
    render = _render_svg if is_svg else _render_raster

    rendered: dict[int, Image.Image] = {}
    for size, name in sorted(OUTPUT_NAMES.items()):
        img = render(source, size)
        rendered[size] = img
        img.save(output_dir / name, "PNG")

    for size in MASKABLE_SIZES:
        maskable = _make_maskable(rendered[size], size)
        maskable.save(output_dir / f"maskable-{size}x{size}.png", "PNG")

    _build_ico(rendered, output_dir / "favicon.ico")

    # Write favicon.svg so browser tab and inline icons stay in sync
    favicon_svg = output_dir / "favicon.svg"
    if is_svg:
        shutil.copy2(source, favicon_svg)
    else:
        # Raster source: embed 32x32 PNG as base64 data-URI in a minimal SVG
        buf = io.BytesIO()
        rendered[32].save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()
        svg_content = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'xmlns:xlink="http://www.w3.org/1999/xlink" '
            'width="32" height="32" viewBox="0 0 32 32">\n'
            f'  <image width="32" height="32" '
            f'xlink:href="data:image/png;base64,{b64}"/>\n'
            '</svg>\n'
        )
        favicon_svg.write_text(svg_content)

    logger.info("Generated all icon variants from %s into %s", source, output_dir)
