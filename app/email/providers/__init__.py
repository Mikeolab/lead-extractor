"""
Email Provider Modules
Supports both SMTP and API-based email providers
"""
from __future__ import annotations

from app.email.providers.base_provider import EmailProvider
from app.email.providers.ses_provider import SESProvider

__all__ = [
    'EmailProvider',
    'SESProvider',
]
