from app.application.ports import Clock, PasswordHasher, TokenService, UnitOfWork, UserRepository
from app.domain.errors import AuthenticationError, ConflictError, ValidationError
from app.domain.ids import persisted_id
from app.domain.users import User

PASSWORD_MIN_LENGTH = 8
INVALID_CREDENTIALS = "invalid credentials"


class AuthService:
    def __init__(
        self,
        users: UserRepository,
        uow: UnitOfWork,
        hasher: PasswordHasher,
        tokens: TokenService,
        clock: Clock,
    ) -> None:
        self._users = users
        self._uow = uow
        self._hasher = hasher
        self._tokens = tokens
        self._clock = clock

    def register(self, email: str, password: str, full_name: str) -> User:
        email = _normalize_email(email)
        full_name = full_name.strip()
        if len(password) < PASSWORD_MIN_LENGTH:
            raise ValidationError(f"password must be at least {PASSWORD_MIN_LENGTH} characters")
        if not full_name:
            raise ValidationError("full name must not be blank")
        if self._users.get_by_email(email) is not None:
            raise ConflictError("email already registered")
        user = self._users.add(
            User(
                id=None,
                email=email,
                full_name=full_name,
                password_hash=self._hasher.hash(password),
                created_at=self._clock.now(),
            )
        )
        self._uow.commit()
        return user

    def login(self, email: str, password: str) -> str:
        user = self._users.get_by_email(_normalize_email(email))
        # Same error and the same hashing work for an unknown email and a wrong password, so
        # neither the message nor the response time reveals which emails are registered.
        # (Registration still answers 409 for a taken email; it is rate limited instead.)
        if user is None:
            self._hasher.verify_dummy(password)
            raise AuthenticationError(INVALID_CREDENTIALS)
        if not self._hasher.verify(password, user.password_hash):
            raise AuthenticationError(INVALID_CREDENTIALS)
        return self._tokens.issue(persisted_id(user.id))

    def resolve_user(self, token: str) -> User:
        user = self._users.get(self._tokens.decode(token))
        if user is None:
            raise AuthenticationError("invalid token")
        return user


def _normalize_email(email: str) -> str:
    return email.strip().lower()
