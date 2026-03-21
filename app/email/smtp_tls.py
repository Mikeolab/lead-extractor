"""
SMTP TLS mode resolution — explicit user choice + safe defaults by port.

- **auto**: port 465 → implicit TLS (`SMTP_SSL`); any other port → plain connect + `STARTTLS`
- **starttls**: always `SMTP` then `STARTTLS` (typical for 587, 25 submission, 2525)
- **ssl**: always `SMTP_SSL` (implicit TLS; typical for 465)
"""
from __future__ import annotations

from typing import Literal

VALID_ENCRYPTION_MODES = frozenset({"auto", "starttls", "ssl"})
ConnectionMode = Literal["starttls", "ssl"]


def normalize_encryption_mode(value: str | None) -> str:
    v = (value or "auto").strip().lower()
    return v if v in VALID_ENCRYPTION_MODES else "auto"


def resolve_connection_mode(smtp_encryption: str | None, port: int) -> ConnectionMode:
    """
    Map stored setting + port to the actual connection class to use.
    """
    enc = normalize_encryption_mode(smtp_encryption)
    p = int(port)
    if enc == "ssl":
        return "ssl"
    if enc == "starttls":
        return "starttls"
    # auto
    return "ssl" if p == 465 else "starttls"


def human_label_for_mode(mode: ConnectionMode) -> str:
    if mode == "ssl":
        return "SSL / implicit TLS (SMTP_SSL)"
    return "STARTTLS (plain socket, then TLS upgrade)"
