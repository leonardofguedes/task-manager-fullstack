"""Domain errors. The API layer maps each one to an HTTP status code."""


class DomainError(Exception):
    """Base class for every business-rule violation."""


class ValidationError(DomainError):
    """Input breaks an invariant (422)."""


class NotFoundError(DomainError):
    """Referenced entity does not exist (404)."""

    def __init__(self, entity: str, entity_id: int) -> None:
        super().__init__(f"{entity} {entity_id} not found")
        self.entity = entity
        self.entity_id = entity_id


class PermissionDeniedError(DomainError):
    """Actor is authenticated but not allowed to perform the action (403)."""


class ConflictError(DomainError):
    """Action conflicts with existing state, e.g. duplicate email (409)."""


class AuthenticationError(DomainError):
    """Credentials or token are missing, invalid or expired (401)."""
