from pwdlib import PasswordHash


class Argon2Hasher:
    """PasswordHasher adapter using Argon2id (OWASP-recommended)."""

    def __init__(self) -> None:
        self._hash = PasswordHash.recommended()

    def hash(self, plain: str) -> str:
        return self._hash.hash(plain)

    def verify(self, plain: str, hashed: str) -> bool:
        return self._hash.verify(plain, hashed)
