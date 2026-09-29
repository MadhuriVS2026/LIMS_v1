"""Domain-level exceptions — raised by entities and domain services."""


class DomainException(Exception):
    """Base class for all domain exceptions."""


class EntityNotFoundError(DomainException):
    """Raised when a requested entity does not exist."""


class DuplicateEntityError(DomainException):
    """Raised when a uniqueness constraint would be violated (e.g. duplicate code)."""


class InvalidStateTransitionError(DomainException):
    """Raised when an entity is asked to transition to an invalid state."""


class NoActiveSpecificationError(DomainException):
    """Raised when logging a Sample for a Product with no Active Specification."""


class ESignatureVerificationError(DomainException):
    """Raised when an electronic signature password check fails."""


class AccountLockedError(DomainException):
    """Raised when a login attempt is made against a locked account."""
