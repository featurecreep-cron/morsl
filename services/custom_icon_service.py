from __future__ import annotations

import os
import re
from typing import Any, Dict, List

from defusedxml import ElementTree as ET
from py_svg_hush import filter_svg
from slugify import slugify

_VALID_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def _slugify_filename(name: str) -> str:
    """Convert filename to a URL-safe slug (strips extension first)."""
    return slugify(os.path.splitext(name)[0]) or "icon"


def _sanitize_svg(raw: bytes) -> str:
    """Parse and sanitize SVG content.

    Uses defusedxml for initial parse (reject malformed XML),
    then py-svg-hush for allowlist-based sanitization.
    """
    # Reject malformed / malicious XML before sanitizing
    ET.fromstring(raw)
    sanitized = filter_svg(raw)
    return sanitized.decode("utf-8")


class CustomIconService:
    """File-based storage for user-uploaded SVG icons."""

    def __init__(self, data_dir: str = "data") -> None:
        self.icons_dir = os.path.join(data_dir, "custom-icons")
        os.makedirs(self.icons_dir, exist_ok=True)

    def list_icons(self) -> List[Dict[str, Any]]:
        """Return list of {key, name} for all custom icons."""
        result = []
        for fname in sorted(os.listdir(self.icons_dir)):
            if fname.endswith(".svg"):
                name = fname[:-4]
                result.append({"key": f"custom:{name}", "name": name})
        return result

    def save_icon(self, filename: str, content: bytes) -> Dict[str, Any]:
        """Sanitize and save an uploaded SVG. Returns {key, name}."""
        slug = _slugify_filename(filename)

        # Deduplicate
        base_slug = slug
        counter = 2
        while os.path.exists(os.path.join(self.icons_dir, f"{slug}.svg")):
            slug = f"{base_slug}-{counter}"
            counter += 1

        sanitized = _sanitize_svg(content)
        path = os.path.join(self.icons_dir, f"{slug}.svg")
        with open(path, "w") as f:
            f.write(sanitized)

        return {"key": f"custom:{slug}", "name": slug}

    def _validate_name(self, name: str) -> None:
        """Reject names that could escape icons_dir (path traversal)."""
        if not name or not _VALID_NAME_RE.match(name):
            raise ValueError(f"Invalid icon name: {name}")

    def get_svg(self, name: str) -> str:
        """Return SVG content for the given icon name. Raises FileNotFoundError."""
        self._validate_name(name)
        path = os.path.join(self.icons_dir, f"{name}.svg")
        if not os.path.isfile(path):
            raise FileNotFoundError(f"Custom icon not found: {name}")
        with open(path) as f:
            return f.read()

    def get_all_svgs(self) -> Dict[str, str]:
        """Return {key: svg_string} for all custom icons."""
        result = {}
        for fname in sorted(os.listdir(self.icons_dir)):
            if fname.endswith(".svg"):
                name = fname[:-4]
                path = os.path.join(self.icons_dir, fname)
                with open(path) as f:
                    result[f"custom:{name}"] = f.read()
        return result

    def rename_icon(self, old_name: str, new_name: str) -> Dict[str, Any]:
        """Rename a custom icon. Returns new {key, name}. Raises FileNotFoundError/ValueError."""
        self._validate_name(old_name)
        new_slug = _slugify_filename(new_name)
        if not _VALID_NAME_RE.match(new_slug):
            raise ValueError(f"Invalid new name: {new_slug}")
        if old_name == new_slug:
            return {"key": f"custom:{old_name}", "name": old_name}
        old_path = os.path.join(self.icons_dir, f"{old_name}.svg")
        if not os.path.isfile(old_path):
            raise FileNotFoundError(f"Custom icon not found: {old_name}")
        new_path = os.path.join(self.icons_dir, f"{new_slug}.svg")
        if os.path.exists(new_path):
            raise ValueError(f"Icon '{new_slug}' already exists")
        os.rename(old_path, new_path)
        return {"key": f"custom:{new_slug}", "name": new_slug}

    def delete_icon(self, name: str) -> None:
        """Delete a custom icon file. Raises FileNotFoundError."""
        self._validate_name(name)
        path = os.path.join(self.icons_dir, f"{name}.svg")
        if not os.path.isfile(path):
            raise FileNotFoundError(f"Custom icon not found: {name}")
        os.unlink(path)
