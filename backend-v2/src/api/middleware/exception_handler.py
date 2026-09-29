"""Global exception handler middleware — maps domain/application exceptions to HTTP responses."""
import json

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from src.application.exceptions.application_exceptions import ApplicationException
from src.domain.exceptions.domain_exceptions import (
    AccountLockedError,
    DomainException,
    DuplicateEntityError,
    EntityNotFoundError,
    ESignatureVerificationError,
    InvalidStateTransitionError,
    NoActiveSpecificationError,
)
from src.observability.structured_logger import get_logger

logger = get_logger("exceptions")

_DOMAIN_STATUS_MAP = {
    EntityNotFoundError: 404,
    DuplicateEntityError: 409,
    InvalidStateTransitionError: 400,
    NoActiveSpecificationError: 400,
    ESignatureVerificationError: 400,
    AccountLockedError: 423,
}


class ExceptionHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except ApplicationException as exc:
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})
        except DomainException as exc:
            status_code = 400
            for exc_type, code in _DOMAIN_STATUS_MAP.items():
                if isinstance(exc, exc_type):
                    status_code = code
                    break
            return JSONResponse(status_code=status_code, content={"detail": str(exc)})
        except Exception as exc:  # noqa: BLE001
            logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
            return JSONResponse(status_code=500, content={"detail": "Internal server error"})
