"""Secure token storage with AES-256-GCM encryption.

Stores OAuth tokens in encrypted files in user's home directory.
Uses same encryption pattern as Gemini CLI and Qwen Code providers.
"""

import json
import os
from pathlib import Path
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class TokenStorage:
    """Secure storage for OAuth tokens using AES-256-GCM encryption."""

    def __init__(self, storage_dir: Optional[Path] = None):
        """Initialize token storage.

        Args:
            storage_dir: Directory to store encrypted tokens.
                        Defaults to ~/.consult7/
        """
        if storage_dir is None:
            storage_dir = Path.home() / ".consult7"

        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Derive encryption key from machine-specific data
        # This is similar to how other providers handle encryption
        self._key = self._get_or_create_key()

    def _get_or_create_key(self) -> bytes:
        """Get or create encryption key.

        Returns:
            32-byte encryption key

        Note:
            In production, this should use a more secure key derivation method.
            For now, we generate a random key and store it locally.
        """
        key_file = self.storage_dir / ".key"

        if key_file.exists():
            return key_file.read_bytes()

        # Generate new 256-bit key
        key = AESGCM.generate_key(bit_length=256)
        key_file.write_bytes(key)
        key_file.chmod(0o600)  # Read/write for owner only
        return key

    def _get_token_path(self, provider: str) -> Path:
        """Get path to encrypted token file for provider.

        Args:
            provider: Provider name (e.g., 'github', 'gemini', 'qwen')

        Returns:
            Path to encrypted token file
        """
        return self.storage_dir / f"{provider}_oauth_token.enc"

    def save_token(self, provider: str, token_data: dict) -> None:
        """Save encrypted OAuth token for provider.

        Args:
            provider: Provider name
            token_data: Token data to encrypt and store
        """
        token_path = self._get_token_path(provider)

        # Serialize token data
        plaintext = json.dumps(token_data).encode("utf-8")

        # Encrypt with AES-256-GCM
        aesgcm = AESGCM(self._key)
        nonce = os.urandom(12)  # 96-bit nonce for GCM
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)

        # Store nonce + ciphertext
        encrypted_data = nonce + ciphertext
        token_path.write_bytes(encrypted_data)
        token_path.chmod(0o600)  # Read/write for owner only

    def load_token(self, provider: str) -> Optional[dict]:
        """Load and decrypt OAuth token for provider.

        Args:
            provider: Provider name

        Returns:
            Decrypted token data or None if not found

        Raises:
            Exception: If decryption fails (corrupted or tampered data)
        """
        token_path = self._get_token_path(provider)

        if not token_path.exists():
            return None

        try:
            # Read encrypted data
            encrypted_data = token_path.read_bytes()

            # Extract nonce and ciphertext
            nonce = encrypted_data[:12]
            ciphertext = encrypted_data[12:]

            # Decrypt with AES-256-GCM
            aesgcm = AESGCM(self._key)
            plaintext = aesgcm.decrypt(nonce, ciphertext, None)

            # Deserialize token data
            return json.loads(plaintext.decode("utf-8"))

        except Exception as e:
            raise Exception(
                f"Failed to decrypt token for {provider}.\n"
                f"  Hint: Re-authenticate with: consult7 {provider} oauth:\n"
                f"  Error: {e}"
            )

    def delete_token(self, provider: str) -> None:
        """Delete OAuth token for provider.

        Args:
            provider: Provider name
        """
        token_path = self._get_token_path(provider)
        if token_path.exists():
            token_path.unlink()

    def has_token(self, provider: str) -> bool:
        """Check if provider has stored token.

        Args:
            provider: Provider name

        Returns:
            True if token exists, False otherwise
        """
        return self._get_token_path(provider).exists()
