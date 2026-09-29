"""
Import all ORM models so they register with Base.metadata.
This ensures FK relationships can be resolved across tables.
"""
from src.infrastructure.database.models.audit_log_model import (  # noqa: F401
    AuditLogModel,
    SAPIntegrationLogModel,
)
from src.infrastructure.database.models.base_model import BaseModel  # noqa: F401
from src.infrastructure.database.models.coa_model import (  # noqa: F401
    CertificateOfAnalysisModel,
)
from src.infrastructure.database.models.instrument_model import (  # noqa: F401
    InstrumentCalibrationModel,
    InstrumentModel,
)
from src.infrastructure.database.models.mrn_model import (  # noqa: F401
    ConsumptionPostingModel,
    MaterialRequisitionModel,
    MRNLineItemModel,
    MRNMaterialLotModel,
)
from src.infrastructure.database.models.oos_model import OOSInvestigationModel  # noqa: F401
from src.infrastructure.database.models.product_model import ProductModel  # noqa: F401
from src.infrastructure.database.models.resource_models import (  # noqa: F401
    ChemicalReagentModel,
    ColumnMasterModel,
    ReferenceStandardModel,
    VolumetricSolutionModel,
)
from src.infrastructure.database.models.sample_model import (  # noqa: F401
    SampleModel,
    SampleResultModel,
)
from src.infrastructure.database.models.specification_model import (  # noqa: F401
    SpecificationModel,
    SpecificationTestModel,
)
from src.infrastructure.database.models.stability_model import (  # noqa: F401
    StabilityMatrixCellModel,
    StabilityProtocolModel,
    StabilityReportModel,
    StabilitySampleModel,
)
from src.infrastructure.database.models.test_model import TestModel  # noqa: F401
from src.infrastructure.database.models.test_template_model import (  # noqa: F401
    TestTemplateModel,
    TestWorksheetModel,
)
from src.infrastructure.database.models.trf_attachment_model import (  # noqa: F401
    TRFAttachmentModel,
)
from src.infrastructure.database.models.trf_model import (  # noqa: F401
    TestRequestFormModel,
    TRFTestLineModel,
)
from src.infrastructure.database.models.user_model import UserModel  # noqa: F401
