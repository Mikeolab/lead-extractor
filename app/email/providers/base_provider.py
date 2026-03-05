"""
Base Email Provider Interface
All providers (SMTP and API) implement this interface
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Optional


class EmailProvider(ABC):
    """Base class for all email providers"""
    
    @abstractmethod
    def send_email(
        self,
        from_email: str,
        to_email: str,
        subject: str,
        body: str,
        is_html: bool = True,
        **kwargs
    ) -> bool:
        """
        Send email
        
        Args:
            from_email: Sender email address
            to_email: Recipient email address
            subject: Email subject
            body: Email body (HTML or plain text)
            is_html: Whether body is HTML (default: True)
            **kwargs: Additional provider-specific arguments
        
        Returns:
            True if sent successfully, False otherwise
        
        Raises:
            Exception: If sending fails
        """
        pass
    
    @abstractmethod
    def test_connection(self) -> bool:
        """
        Test if provider is working
        
        Returns:
            True if connection OK, False otherwise
        """
        pass
    
    @abstractmethod
    def get_daily_limit(self) -> int:
        """
        Get daily sending limit for this provider
        
        Returns:
            Daily limit (e.g., 300 for Brevo, 500 for Gmail, unlimited for Mailgun verified)
        """
        pass
