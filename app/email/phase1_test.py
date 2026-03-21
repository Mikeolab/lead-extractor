"""
Phase 1 Email Infrastructure Test Runner

Safe utilities to:
- add a mailbox (credentials encrypted at rest)
- test SMTP connection (login)
- optionally send a single test email

This intentionally does NOT touch campaign/queue processing (Phase 2+).
"""

from __future__ import annotations

import argparse
import getpass
import os
import sys
from typing import Optional

from app.email.mailbox_pool import MailboxPool
from app.email.rate_limiter import RateLimiter
from app.email.smtp_pool import SMTPConnectionPool


def _mask(s: str, keep: int = 3) -> str:
    if not s:
        return ""
    if len(s) <= keep * 2:
        return "*" * len(s)
    return f"{s[:keep]}***{s[-keep:]}"


def _print_mailboxes(pool: MailboxPool) -> None:
    rows = pool.get_all_mailboxes()
    if not rows:
        print("No mailboxes found.")
        return

    print("Mailboxes:")
    for mb in rows:
        print(
            f"- id={mb['id']} name={mb['name']!r} email={mb['email']} "
            f"provider={mb['provider']} active={bool(mb['is_active'])} "
            f"sent_today={mb['sent_today']}/{mb['daily_limit']} errors={mb['error_count']}"
        )


def _resolve_password(arg_password: Optional[str]) -> str:
    if arg_password:
        return arg_password
    env_pw = os.getenv("SMTP_PASSWORD") or os.getenv("LEAD_EXTRACTOR_SMTP_PASSWORD")
    if env_pw:
        return env_pw
    return getpass.getpass("SMTP app password (input hidden): ").strip()


def add_mailbox(args: argparse.Namespace) -> int:
    pool = MailboxPool()

    smtp_password = _resolve_password(args.smtp_password)
    if not smtp_password:
        raise SystemExit("Missing SMTP password (use --smtp-password or SMTP_PASSWORD env var).")

    mailbox_id = pool.add_mailbox(
        name=args.name,
        email=args.email,
        provider=args.provider,
        smtp_host=args.smtp_host,
        smtp_port=args.smtp_port,
        smtp_username=args.smtp_username or args.email,
        smtp_password=smtp_password,
        daily_limit=args.daily_limit,
        smtp_encryption=args.smtp_encryption,
    )

    print(
        "Mailbox added:"
        f" id={mailbox_id} email={args.email} provider={args.provider} "
        f"smtp={args.smtp_host}:{args.smtp_port} username={args.smtp_username or args.email} "
        f"password={_mask(smtp_password)}"
    )
    return mailbox_id


def test_connection(args: argparse.Namespace) -> None:
    pool = MailboxPool()
    ok, msg = pool.test_connection(args.mailbox_id)
    if ok:
        print(f"✅ SMTP login OK for mailbox id={args.mailbox_id}")
        print(msg)
        return
    print(msg)
    raise SystemExit(f"❌ SMTP login FAILED for mailbox id={args.mailbox_id}")


def send_test_email(args: argparse.Namespace) -> None:
    pool = MailboxPool()
    limiter = RateLimiter()
    smtp_pool = SMTPConnectionPool(max_connections_per_mailbox=5)

    # Prefer explicit mailbox id if provided; otherwise use next available.
    if args.mailbox_id is not None:
        # Internal helper is intentionally private, but for a test runner it’s fine.
        mailbox = pool._get_mailbox_by_id(args.mailbox_id)  # type: ignore[attr-defined]
    else:
        mailbox = pool.get_available_mailbox()

    if not mailbox:
        raise SystemExit("No available mailbox (none active or all at daily limit).")

    mailbox_id = mailbox["id"]
    from_email = mailbox["email"]
    to_email = args.to_email
    subject = args.subject
    body = args.body

    if not limiter.can_send(mailbox_id):
        print("Rate limited right now; waiting a randomized delay...")
        import time

        time.sleep(limiter.get_delay())

    conn = None
    try:
        conn = smtp_pool.get_connection(mailbox)
        if not conn:
            raise RuntimeError("No SMTP connection available (pool exhausted).")

        smtp_pool.send_email(
            conn=conn,
            from_email=from_email,
            to_email=to_email,
            subject=subject,
            body=body,
            is_html=args.html,
        )

        pool.mark_sent(mailbox_id)
        limiter.record_sent(mailbox_id)
        print(f"✅ Sent test email from {from_email} to {to_email} using mailbox id={mailbox_id}")
    except Exception as e:
        try:
            pool.mark_error(mailbox_id, str(e))
        except Exception:
            pass
        raise
    finally:
        if conn is not None:
            smtp_pool.return_connection(mailbox_id, conn)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Phase 1 email infrastructure tester")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub_list = sub.add_parser("list", help="List mailboxes")
    sub_list.set_defaults(func=lambda a: _print_mailboxes(MailboxPool()))

    sub_add = sub.add_parser("add-mailbox", help="Add a mailbox (credentials encrypted)")
    sub_add.add_argument("--name", required=True)
    sub_add.add_argument("--email", required=True)
    sub_add.add_argument("--provider", default="gmail", choices=["gmail", "outlook", "custom"])
    sub_add.add_argument("--smtp-host", default="smtp.gmail.com")
    sub_add.add_argument("--smtp-port", type=int, default=587)
    sub_add.add_argument("--smtp-username", default=None)
    sub_add.add_argument("--smtp-password", default=None, help="Prefer SMTP_PASSWORD env var instead")
    sub_add.add_argument("--daily-limit", type=int, default=500)
    sub_add.add_argument(
        "--smtp-encryption",
        default="auto",
        choices=["auto", "starttls", "ssl"],
        help="TLS mode: auto (465=SSL, else STARTTLS), starttls, or ssl (implicit TLS)",
    )
    sub_add.set_defaults(func=add_mailbox)

    sub_test = sub.add_parser("test-connection", help="Test SMTP login for a mailbox id")
    sub_test.add_argument("--mailbox-id", type=int, required=True)
    sub_test.set_defaults(func=test_connection)

    sub_send = sub.add_parser("send-test", help="Send ONE test email (no queue)")
    sub_send.add_argument("--mailbox-id", type=int, default=None, help="If omitted, uses next available mailbox")
    sub_send.add_argument("--to-email", required=True)
    sub_send.add_argument("--subject", default="Lead Extractor Pro: SMTP test")
    sub_send.add_argument(
        "--body",
        default="<p>If you received this, Phase 1 SMTP is working.</p>",
        help="HTML by default; use --no-html for plain text",
    )
    sub_send.add_argument("--html", action=argparse.BooleanOptionalAction, default=True)
    sub_send.set_defaults(func=send_test_email)

    return p


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        result = args.func(args)
        return 0 if result is None else 0
    except KeyboardInterrupt:
        print("\nCancelled.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())

