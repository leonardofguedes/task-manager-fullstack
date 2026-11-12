from datetime import timedelta

import jwt

from app.application.ports import Clock
from app.domain.errors import AuthenticationError


class JwtTokenService:
    """TokenService adapter: signed JWT access tokens with `sub` = user id."""

    def __init__(self, secret: str, algorithm: str, expire_minutes: int, clock: Clock) -> None:
        self._secret = secret
        self._algorithm = algorithm
        self._ttl = timedelta(minutes=expire_minutes)
        self._clock = clock

    def issue(self, user_id: int) -> str:
        now = self._clock.now()
        payload = {"sub": str(user_id), "iat": now, "exp": now + self._ttl}
        return jwt.encode(payload, self._secret, algorithm=self._algorithm)

    def decode(self, token: str) -> int:
        try:
            # `algorithms` is pinned: tokens signed with "none" or another algorithm are rejected.
            payload = jwt.decode(
                token,
                self._secret,
                algorithms=[self._algorithm],
                options={"require": ["sub", "exp"]},
            )
            return int(payload["sub"])
        except (jwt.PyJWTError, ValueError) as exc:
            raise AuthenticationError("invalid or expired token") from exc
