"""
Credential Encryption Manager
Securely stores and retrieves mailbox credentials using OS keychain
"""
from __future__ import annotations
import base64
from cryptography.fernet import Fernet
import keyring
import sys
from pathlib import Path

# Service name for keyring
KEYRING_SERVICE = "LeadExtractorPro"


class CredentialManager:
    """Manages encryption/decryption of mailbox credentials"""
    
    def __init__(self):
        self.master_key = self._get_or_create_master_key()
        self.cipher = Fernet(self.master_key)
    
    def _get_or_create_master_key(self) -> bytes:
        """Get master encryption key from OS keychain or create new one"""
        try:
            # Try to get existing key
            key_str = keyring.get_password(KEYRING_SERVICE, "master_key")
            if key_str:
                return key_str.encode()
        except Exception:
            pass
        
        # Create new key
        key = Fernet.generate_key()
        try:
            keyring.set_password(KEYRING_SERVICE, "master_key", key.decode())
        except Exception as e:
            # Fallback: store in local file (less secure but works)
            key_file = Path.home() / ".lead_extractor" / "master_key.key"
            key_file.parent.mkdir(parents=True, exist_ok=True)
            key_file.write_bytes(key)
        
        return key
    
    def encrypt(self, plaintext: str) -> str:
        """Encrypt a plaintext string"""
        if not plaintext:
            return ""
        encrypted = self.cipher.encrypt(plaintext.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
    
    def decrypt(self, encrypted: str) -> str:
        """Decrypt an encrypted string"""
        if not encrypted:
            return ""
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted.encode())
            decrypted = self.cipher.decrypt(encrypted_bytes)
            return decrypted.decode()
        except Exception as e:
            raise ValueError(f"Failed to decrypt: {str(e)}")


# Global instance
_credential_manager = None

def get_credential_manager() -> CredentialManager:
    """Get global credential manager instance"""
    global _credential_manager
    if _credential_manager is None:
        _credential_manager = CredentialManager()
    return _credential_manager

