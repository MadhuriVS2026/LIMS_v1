"""
Dependency Injection container.
Wires domain interfaces to infrastructure implementations.
"""
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.attachment_service import AttachmentService
from src.application.services.attachment_service import AttachmentService
from src.application.services.auth_service import AuthService
from src.application.services.coa_service import COAService
from src.application.services.mrn_service import MRNService
from src.application.services.oos_service import OOSService
from src.application.services.product_service import ProductService
from src.application.services.resource_service import ResourceService
from src.application.services.sample_service import SampleService
from src.application.services.sap_integration_service import SAPIntegrationService
from src.application.services.specification_service import SpecificationService
from src.application.services.stability_service import StabilityService
from src.application.services.test_service import TestService
from src.application.services.test_template_service import TestTemplateService
from src.application.services.trf_service import TRFService
from src.application.services.user_service import UserService
from src.application.services.worksheet_service import WorksheetService
from src.infrastructure.database.repositories.audit_repository_impl import (
    AuditLogRepositoryImpl,
    SAPIntegrationLogRepositoryImpl,
    SAPReceivedLotRepositoryImpl,
)
from src.infrastructure.database.repositories.coa_repository_impl import COARepositoryImpl
from src.infrastructure.database.repositories.mrn_repository_impl import (
    ConsumptionPostingRepositoryImpl,
    MaterialRequisitionRepositoryImpl,
    MRNMaterialLotRepositoryImpl,
)
from src.infrastructure.database.repositories.oos_repository_impl import OOSRepositoryImpl
from src.infrastructure.database.repositories.product_repository_impl import (
    ProductRepositoryImpl,
)
from src.infrastructure.database.repositories.resource_repositories_impl import (
    ChemicalRepositoryImpl,
    ColumnRepositoryImpl,
    InstrumentRepositoryImpl,
    ReferenceStandardRepositoryImpl,
    VolumetricSolutionRepositoryImpl,
)
from src.infrastructure.database.repositories.sample_repository_impl import (
    SampleRepositoryImpl,
)
from src.infrastructure.database.repositories.specification_repository_impl import (
    SpecificationRepositoryImpl,
)
from src.infrastructure.database.repositories.stability_repository_impl import (
    StabilityRepositoryImpl,
)
from src.infrastructure.database.repositories.test_repository_impl import (
    TestRepositoryImpl,
)
from src.infrastructure.database.repositories.test_template_repository_impl import (
    TestTemplateRepositoryImpl,
    TestWorksheetRepositoryImpl,
)
from src.infrastructure.database.repositories.trf_attachment_repository_impl import (
    TRFAttachmentRepositoryImpl,
)
from src.infrastructure.database.repositories.trf_attachment_repository_impl import (
    TRFAttachmentRepositoryImpl,
)
from src.infrastructure.database.repositories.trf_repository_impl import (
    TRFRepositoryImpl,
)
from src.infrastructure.database.repositories.user_repository_impl import (
    UserRepositoryImpl,
)
from src.config.settings import settings
from src.infrastructure.external.sap.sap_client import (
    ISAPClient,
    SAPIntegrationSuiteClient,
    SimulatedSAPClient,
)
from src.infrastructure.security.jwt_provider import JWTProvider


class Container:
    """Simple DI container wiring repositories -> application services."""

    @staticmethod
    def get_jwt_provider() -> JWTProvider:
        return JWTProvider()

    @staticmethod
    def get_auth_service(session: AsyncSession) -> AuthService:
        return AuthService(
            UserRepositoryImpl(session), AuditLogRepositoryImpl(session), Container.get_jwt_provider()
        )

    @staticmethod
    def get_user_service(session: AsyncSession) -> UserService:
        return UserService(UserRepositoryImpl(session), AuditLogRepositoryImpl(session))

    @staticmethod
    def get_product_service(session: AsyncSession) -> ProductService:
        return ProductService(ProductRepositoryImpl(session), AuditLogRepositoryImpl(session))

    @staticmethod
    def get_test_service(session: AsyncSession) -> TestService:
        return TestService(TestRepositoryImpl(session), AuditLogRepositoryImpl(session))

    @staticmethod
    def get_specification_service(session: AsyncSession) -> SpecificationService:
        return SpecificationService(SpecificationRepositoryImpl(session), AuditLogRepositoryImpl(session))

    @staticmethod
    def get_sample_service(session: AsyncSession) -> SampleService:
        return SampleService(
            SampleRepositoryImpl(session),
            SpecificationRepositoryImpl(session),
            ProductRepositoryImpl(session),
            TestRepositoryImpl(session),
            OOSRepositoryImpl(session),
            AuditLogRepositoryImpl(session),
            SAPReceivedLotRepositoryImpl(session),
        )

    @staticmethod
    def get_oos_service(session: AsyncSession) -> OOSService:
        return OOSService(
            OOSRepositoryImpl(session), SampleRepositoryImpl(session), AuditLogRepositoryImpl(session)
        )

    @staticmethod
    def get_resource_service(session: AsyncSession) -> ResourceService:
        return ResourceService(
            InstrumentRepositoryImpl(session),
            ColumnRepositoryImpl(session),
            ReferenceStandardRepositoryImpl(session),
            ChemicalRepositoryImpl(session),
            VolumetricSolutionRepositoryImpl(session),
            AuditLogRepositoryImpl(session),
        )

    @staticmethod
    def get_sap_client() -> ISAPClient:
        """
        Returns the live SAP Integration Suite (CPI) client when
        SAP_USE_LIVE_CLIENT=true and credentials are configured; otherwise
        falls back to the in-memory simulator so the app works without SAP.
        """
        if settings.SAP_USE_LIVE_CLIENT and settings.SAP_CPI_BASE_URL:
            return SAPIntegrationSuiteClient(
                base_url=settings.SAP_CPI_BASE_URL,
                username=settings.SAP_CPI_USERNAME,
                password=settings.SAP_CPI_PASSWORD,
                timeout_seconds=settings.SAP_CPI_TIMEOUT_SECONDS,
            )
        return SimulatedSAPClient()

    @staticmethod
    def get_sap_service(session: AsyncSession) -> SAPIntegrationService:
        return SAPIntegrationService(
            Container.get_sap_client(),
            SampleRepositoryImpl(session),
            SAPIntegrationLogRepositoryImpl(session),
            AuditLogRepositoryImpl(session),
            SAPReceivedLotRepositoryImpl(session),
        )

    @staticmethod
    def get_audit_repo(session: AsyncSession) -> AuditLogRepositoryImpl:
        return AuditLogRepositoryImpl(session)

    @staticmethod
    def get_mrn_service(session: AsyncSession) -> MRNService:
        return MRNService(
            MRNMaterialLotRepositoryImpl(session),
            MaterialRequisitionRepositoryImpl(session),
            ConsumptionPostingRepositoryImpl(session),
            Container.get_sap_client(),
            SAPIntegrationLogRepositoryImpl(session),
            AuditLogRepositoryImpl(session),
            settings.MRN_SAP_PLANT_CODE,
        )

    @staticmethod
    def get_trf_service(session: AsyncSession) -> TRFService:
        return TRFService(TRFRepositoryImpl(session), AuditLogRepositoryImpl(session))

    @staticmethod
    def get_test_template_service(session: AsyncSession) -> TestTemplateService:
        return TestTemplateService(
            TestTemplateRepositoryImpl(session),
            TestRepositoryImpl(session),
            AuditLogRepositoryImpl(session),
        )

    @staticmethod
    def get_worksheet_service(session: AsyncSession) -> WorksheetService:
        return WorksheetService(
            TestWorksheetRepositoryImpl(session),
            TestTemplateRepositoryImpl(session),
            TRFRepositoryImpl(session),
            ProductRepositoryImpl(session),
            AuditLogRepositoryImpl(session),
            SpecificationRepositoryImpl(session),
        )

    @staticmethod
    def get_coa_service(session: AsyncSession) -> COAService:
        return COAService(
            COARepositoryImpl(session),
            TRFRepositoryImpl(session),
            TestWorksheetRepositoryImpl(session),
            SpecificationRepositoryImpl(session),
            ProductRepositoryImpl(session),
            AuditLogRepositoryImpl(session),
        )

    @staticmethod
    def get_attachment_service(session: AsyncSession) -> AttachmentService:
        #  Storage config is read from `settings` at call time rather than cached,
        #  so it stays overridable per environment (and per test) without the
        #  container holding process-wide state.
        return AttachmentService(
            TRFAttachmentRepositoryImpl(session),
            TRFRepositoryImpl(session),
            AuditLogRepositoryImpl(session),
            storage_path=settings.ATTACHMENT_STORAGE_PATH,
            max_bytes=settings.ATTACHMENT_MAX_BYTES,
            allowed_content_types=settings.ATTACHMENT_ALLOWED_CONTENT_TYPES,
        )

    @staticmethod
    def get_stability_service(session: AsyncSession) -> StabilityService:
        return StabilityService(
            StabilityRepositoryImpl(session),
            Container.get_sample_service(session),
            AuditLogRepositoryImpl(session),
        )
