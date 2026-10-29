"""Encrypt organization provider credentials; the server owns the encryption key."""
from cryptography.fernet import Fernet, InvalidToken


class LlmSecretError(RuntimeError):
    """A credential cannot be stored/read safely; never expose its original error."""

    def __init__(self) -> None:
        super().__init__('llm_settings_unavailable')


class LlmSecretStore:
    """Use a server Fernet key and versioned ciphertext, never plaintext fallback."""

    def __init__(self, encryption_key: str | None) -> None:
        self._cipher = None
        if encryption_key:
            try:
                self._cipher = Fernet(encryption_key.encode('ascii'))
            except (ValueError, TypeError, UnicodeError):
                raise LlmSecretError() from None

    def encrypt(self, api_key: str | None) -> str | None:
        """Return versioned ciphertext or NULL for a connection without credentials."""
        if not api_key:
            return None
        if self._cipher is None:
            raise LlmSecretError()
        return 'v1:' + self._cipher.encrypt(api_key.encode('utf-8')).decode('ascii')

    def decrypt(self, ciphertext: str | None) -> str:
        """Return the provider key; a missing server key or corrupt token fails closed."""
        if ciphertext is None:
            return ''
        if self._cipher is None or not ciphertext.startswith('v1:'):
            raise LlmSecretError()
        try:
            return self._cipher.decrypt(ciphertext[3:].encode('ascii')).decode('utf-8')
        except (InvalidToken, ValueError, UnicodeError):
            raise LlmSecretError() from None
