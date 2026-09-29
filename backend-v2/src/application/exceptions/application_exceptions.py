"""Application-layer exceptions — raised by services, caught by API middleware."""


class ApplicationException(Exception):
    """Base class for application-layer exceptions."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class NotFoundException(ApplicationException):
    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(message, status_code=404)


class ConflictException(ApplicationException):
    def __init__(self, message: str = "Conflict") -> None:
        super().__init__(message, status_code=409)


class ForbiddenException(ApplicationException):
    def __init__(self, message: str = "Forbidden") -> None:
        super().__init__(message, status_code=403)


class UnauthorizedException(ApplicationException):
    def __init__(self, message: str = "Unauthorized") -> None:
        super().__init__(message, status_code=401)


class ValidationException(ApplicationException):
    def __init__(self, message: str = "Validation failed") -> None:
        super().__init__(message, status_code=400)


class LockedException(ApplicationException):
    def __init__(self, message: str = "Account locked") -> None:
        super().__init__(message, status_code=423)
