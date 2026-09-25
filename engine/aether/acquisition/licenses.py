from __future__ import annotations

import re
from pathlib import Path

from aether.config import settings

LICENSE_FILES = ("LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING", "COPYING.md")

SPDX_MARKERS: list[tuple[str, re.Pattern[str]]] = [
    ("MIT", re.compile(r"\bMIT License\b|\bPermission is hereby granted, free of charge\b", re.I)),
    ("Apache-2.0", re.compile(r"\bApache License\b.*\b2\.0\b|\bLicensed under the Apache License", re.I | re.S)),
    ("BSD-3-Clause", re.compile(r"\bBSD 3-Clause\b|\bNeither the name of", re.I)),
    ("BSD-2-Clause", re.compile(r"\bBSD 2-Clause\b|\bRedistribution and use in source and binary forms", re.I)),
]


def detect_license(root: Path) -> str:
    for name in LICENSE_FILES:
        path = root / name
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for spdx, pat in SPDX_MARKERS:
            if pat.search(text):
                return spdx
        package = root / "package.json"
        if package.is_file():
            raw = package.read_text(encoding="utf-8", errors="ignore")
            m = re.search(r'"license"\s*:\s*"([^"]+)"', raw)
            if m:
                return m.group(1)
        pyproject = root / "pyproject.toml"
        if pyproject.is_file():
            raw = pyproject.read_text(encoding="utf-8", errors="ignore")
            m = re.search(r'license\s*=\s*"([^"]+)"', raw)
            if m:
                return m.group(1)
    package = root / "package.json"
    if package.is_file():
        raw = package.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r'"license"\s*:\s*"([^"]+)"', raw)
        if m:
            return m.group(1)
    return "UNKNOWN"


class LicenseRejected(PermissionError):
    def __init__(self, spdx: str) -> None:
        self.spdx = spdx
        allowed = ", ".join(sorted(settings.allowed_licenses))
        super().__init__(f"License {spdx} is outside the allowlist ({allowed}).")


def license_allowed(spdx: str, allowlist: set[str] | None = None) -> bool:
    allowed = allowlist or settings.allowed_licenses
    return spdx in allowed
