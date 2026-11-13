from pwdlib import PasswordHash


class Argon2Hasher:
    """PasswordHasher adapter using Argon2id (OWASP-recommended)."""

    def __init__(self) -> None:
        self._hash = PasswordHash.recommended()
        # Computed once per process; checking against it costs the same as a real verify.
        self.dummy_hash = self._hash.hash("dummy-password-for-timing")

    def hash(self, plain: str) -> str:
        return self._hash.hash(plain)

    def verify(self, plain: str, hashed: str) -> bool:
        return self._hash.verify(plain, hashed)

    def verify_dummy(self, plain: str) -> None:
        self._hash.verify(plain, self.dummy_hash)
