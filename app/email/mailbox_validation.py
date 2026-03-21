"""
Validation for mailbox / SMTP configuration (UI + server-side guardrails).
"""
from __future__ import annotations

import re
from typing import Any

from email_validator import EmailNotValidError, validate_email

from app.email.smtp_tls import VALID_ENCRYPTION_MODES

# Block accidental submits of tutorial placeholders
_PLACEHOLDER_HOSTS = frozenset(
    {
        "smtp.example.com",
        "example.com",
        "mail.example.com",
        "smtp.yourdomain.com",
    }
)

_MAX_NAME_LEN = 120
_MAX_HOST_LEN = 253
_MAX_PASSWORD_LEN = 2048


def _normalize_hostname(host: str) -> str:
    return (host or "").strip().lower()


def validate_smtp_hostname(host: str) -> tuple[bool, str, str]:
    """
    Returns (ok, message, normalized_host).
    """
    h = _normalize_hostname(host)
    if not h:
        return False, "SMTP host is required.", ""
    if len(h) > _MAX_HOST_LEN:
        return False, f"SMTP host is too long (max {_MAX_HOST_LEN} characters).", h
    if "://" in h:
        return False, "Enter the hostname only (do not include https:// or mailto:).", h
    if "/" in h or "?" in h or "#" in h:
        return False, "Enter the hostname only (no path or query).", h
    if " " in h or "\n" in h or "\t" in h:
        return False, "SMTP host cannot contain spaces.", h
    if h in _PLACEHOLDER_HOSTS:
        return False, "Replace the example host with your real SMTP server hostname.", h
    if h.startswith(".") or h.endswith(".") or ".." in h:
        return False, "SMTP host format is invalid.", h

    # IPv4
    if re.fullmatch(r"(\d{1,3}\.){3}\d{1,3}", h):
        parts = [int(x) for x in h.split(".")]
        if not all(0 <= p <= 255 for p in parts):
            return False, "Invalid IPv4 address for SMTP host.", h
        return True, "", h

    # Hostname / FQDN (labels with dots; allow single hostname for LAN if has letter)
    if not re.fullmatch(
        r"([a-z0-9]([a-z0-9\-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}",
        h,
    ):
        if h == "localhost" or re.fullmatch(r"[a-z0-9][a-z0-9\-]{0,62}", h):
            return True, "", h
        return (
            False,
            "SMTP host should look like mail.yourdomain.com or an IPv4 address.",
            h,
        )

    return True, "", h


def validate_smtp_port(port: Any) -> tuple[bool, str, int]:
    try:
        p = int(port)
    except (TypeError, ValueError):
        return False, "SMTP port must be a number.", 0
    if p < 1 or p > 65535:
        return False, "SMTP port must be between 1 and 65535.", p
    return True, "", p


def validate_mailbox_email(email: str) -> tuple[bool, str, str]:
    raw = (email or "").strip()
    if not raw:
        return False, "Email address is required.", ""
    try:
        v = validate_email(raw, check_deliverability=False)
        return True, "", v.email
    except EmailNotValidError as e:
        return False, f"Invalid email address: {e}", raw


def validate_smtp_mailbox(
    *,
    name: str,
    email: str,
    smtp_host: str,
    smtp_port: Any,
    smtp_username: str,
    smtp_password: str,
    daily_limit: Any,
    provider: str,
    smtp_encryption: str = "auto",
) -> tuple[bool, list[str], dict[str, Any] | None]:
    """
    Full validation for SMTP-backed mailboxes (gmail, outlook, custom).
    Returns (ok, error_messages, normalized_fields).
    """
    errors: list[str] = []

    n = (name or "").strip()
    if not n:
        errors.append("Name is required (e.g. 'Work SMTP').")
    elif len(n) > _MAX_NAME_LEN:
        errors.append(f"Name is too long (max {_MAX_NAME_LEN} characters).")

    ok_e, msg_e, email_norm = validate_mailbox_email(email)
    if not ok_e:
        errors.append(msg_e)

    ok_h, msg_h, host_norm = validate_smtp_hostname(smtp_host)
    if not ok_h:
        errors.append(msg_h)

    ok_p, msg_p, port_int = validate_smtp_port(smtp_port)
    if not ok_p:
        errors.append(msg_p)

    user = (smtp_username or "").strip()
    if not user:
        errors.append("SMTP username is required (usually your full email address).")

    pwd_raw = smtp_password
    pwd = pwd_raw.strip() if isinstance(pwd_raw, str) else pwd_raw
    if not pwd:
        errors.append("SMTP password is required.")
    elif isinstance(pwd, str) and len(pwd) > _MAX_PASSWORD_LEN:
        errors.append("SMTP password is unusually long; check for paste errors.")

    try:
        dl = int(daily_limit)
    except (TypeError, ValueError):
        errors.append("Daily limit must be a whole number.")
        dl = 0
    if dl < 1:
        errors.append("Daily limit must be at least 1.")
    if dl > 1_000_000:
        errors.append("Daily limit is too large (max 1,000,000).")

    prov = (provider or "custom").strip().lower()
    if prov not in ("gmail", "outlook", "custom", "aws_ses"):
        errors.append("Invalid provider.")

    enc_norm = (smtp_encryption or "auto").strip().lower()
    if enc_norm not in VALID_ENCRYPTION_MODES:
        errors.append(
            "Invalid SMTP encryption. Use Auto, STARTTLS, or SSL / implicit TLS."
        )

    if errors:
        return False, errors, None

    # Hints (not errors): unusual ports
    if port_int not in (25, 465, 587, 2525, 2587):
        pass  # still allowed; provider-specific

    pwd_out = pwd if isinstance(pwd, str) else (str(pwd_raw) if pwd_raw is not None else "")
    return True, [], {
        "name": n,
        "email": email_norm,
        "smtp_host": host_norm,
        "smtp_port": port_int,
        "smtp_username": user,
        "smtp_password": pwd_out,
        "daily_limit": dl,
        "provider": prov,
        "smtp_encryption": enc_norm,
    }


def validate_aws_ses_mailbox(
    *,
    name: str,
    email: str,
    aws_access_key: str,
    aws_secret_key: str,
    aws_region: str,
    daily_limit: Any,
) -> tuple[bool, list[str], dict[str, Any] | None]:
    errors: list[str] = []
    n = (name or "").strip()
    if not n:
        errors.append("Name is required.")
    elif len(n) > _MAX_NAME_LEN:
        errors.append(f"Name is too long (max {_MAX_NAME_LEN} characters).")
    ok_e, msg_e, email_norm = validate_mailbox_email(email)
    if not ok_e:
        errors.append(msg_e)
    ak = (aws_access_key or "").strip()
    sk = (aws_secret_key or "").strip()
    if not ak:
        errors.append("AWS Access Key ID is required.")
    if not sk:
        errors.append("AWS Secret Access Key is required.")
    reg = (aws_region or "").strip().lower()
    if not reg:
        errors.append("AWS Region is required.")
    elif len(reg) > 32 or not re.fullmatch(r"[a-z0-9\-]+", reg):
        errors.append(
            "AWS Region should look like us-east-1 (letters, numbers, hyphens only)."
        )
    try:
        dl = int(daily_limit)
    except (TypeError, ValueError):
        errors.append("Daily limit must be a number.")
        dl = 0
    if dl < 1:
        errors.append("Daily limit must be at least 1.")
    if dl > 1_000_000:
        errors.append("Daily limit is too large (max 1,000,000).")
    if errors:
        return False, errors, None
    return True, [], {
        "name": n,
        "email": email_norm,
        "daily_limit": dl,
        "aws_access_key": ak,
        "aws_secret_key": sk,
        "aws_region": reg,
    }
