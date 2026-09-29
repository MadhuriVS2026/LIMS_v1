"""
Application settings using Pydantic BaseSettings.
Loads configuration from environment variables and .env files.
"""
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Enterprise application configuration for Anti Gravity LIMS."""

    APP_NAME: str = Field(default="Anti Gravity LIMS", description="Application name")
    APP_VERSION: str = Field(default="2.0.0", description="Application version")
    DEBUG: bool = Field(default=False, description="Debug mode")

    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./lims.db",
        description="Async database connection string",
    )
    DB_POOL_SIZE: int = Field(default=20, description="Database connection pool size")
    DB_MAX_OVERFLOW: int = Field(default=10, description="Max overflow connections")

    JWT_SECRET_KEY: str = Field(
        default="change-me-in-production-use-strong-secret",
        description="JWT signing secret key",
    )
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=480, description="Access token expiry in minutes (8hr lab shift)"
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=7, description="Refresh token expiry in days"
    )

    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    LOG_FILE_PATH: str = Field(
        default="logs/application.log", description="Log file path"
    )
    LOG_MAX_BYTES: int = Field(
        default=10 * 1024 * 1024, description="Max log file size (10MB)"
    )
    LOG_BACKUP_COUNT: int = Field(default=10, description="Number of log backups")

    CORS_ORIGINS: list[str] = Field(
        default=["http://localhost:5173", "http://127.0.0.1:5173"],
        description="Allowed CORS origins",
    )

    # SAP Integration Suite (CPI) — HTTP integration flows (LIMS QAS collection)
    SAP_CPI_BASE_URL: str = Field(
        default="", description="Base URL of the SAP Integration Suite tenant"
    )
    SAP_CPI_USERNAME: str = Field(
        default="", description="OAuth client / basic-auth username for CPI"
    )
    SAP_CPI_PASSWORD: str = Field(
        default="", description="OAuth client secret / basic-auth password for CPI"
    )
    SAP_CPI_TIMEOUT_SECONDS: int = Field(
        default=30, description="HTTP timeout for SAP CPI calls"
    )
    SAP_USE_LIVE_CLIENT: bool = Field(
        default=False, description="If true, wire the live SAP CPI client instead of the simulator"
    )
    SAP_INBOUND_API_KEY: str = Field(
        default="",
        description=(
            "Shared secret that SAP CPI must send as the x-api-key header when pushing "
            "inspection lot data to /api/v1/sap/inbound/inspection-lot. If left blank, "
            "the inbound endpoint accepts calls without a key (dev only) and logs a warning."
        ),
    )

    # TRF attachments — chromatogram PDFs and raw-data files
    ATTACHMENT_STORAGE_PATH: str = Field(
        default="storage/attachments",
        description=(
            "Directory holding uploaded attachment bytes. Files are written under "
            "generated storage names; the directory must NOT be web-exposed, since "
            "downloads are authorised and streamed through the API."
        ),
    )
    ATTACHMENT_MAX_BYTES: int = Field(
        default=25 * 1024 * 1024,
        description="Maximum accepted upload size (25MB). A chromatogram PDF is well under this.",
    )
    ATTACHMENT_ALLOWED_CONTENT_TYPES: list[str] = Field(
        default=[
            "application/pdf",
            "image/png",
            "image/jpeg",
            "text/csv",
        ],
        description=(
            "Allow-list of accepted content types. Declared type is checked against this "
            "list AND against the file's own signature, so renaming an executable to .pdf "
            "is rejected."
        ),
    )

    # MRN — Material Requisition & Consumption module
    MRN_SAP_PLANT_CODE: str = Field(
        default="",
        description=(
            "R&D plant code used to filter the GRN-completed material pull "
            "(ISAPClient.read_grn_completed_materials). Must be configured per "
            "environment, not hardcoded — the real value is pending confirmation "
            "with SAP CoE."
        ),
    )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


settings = Settings()
