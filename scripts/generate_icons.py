#!/usr/bin/env python3
"""Generate all favicon/icon variants from favicon.svg.

Renders the SVG at multiple sizes, creates maskable variants,
and rebuilds favicon.ico.

Usage:
    python scripts/generate_icons.py
"""

from __future__ import annotations

from pathlib import Path

from morsl.services.icon_service import generate_icons

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ICONS_DIR = PROJECT_ROOT / "web" / "icons"
SVG_SOURCE = ICONS_DIR / "default-favicon.svg"


def main() -> None:
    if not SVG_SOURCE.exists():
        print(f"Error: {SVG_SOURCE} not found")
        return

    print(f"Source: {SVG_SOURCE.relative_to(PROJECT_ROOT)}")
    generate_icons(SVG_SOURCE, ICONS_DIR)
    print(f"Done! All icons written to {ICONS_DIR.relative_to(PROJECT_ROOT)}/")


if __name__ == "__main__":
    main()
