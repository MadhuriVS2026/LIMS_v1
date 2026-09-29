"""API v1 router aggregation."""
from fastapi import APIRouter

from src.api.v1.endpoints.attachment_endpoints import router as attachment_router
from src.api.v1.endpoints.attachment_endpoints import router as attachment_router
from src.api.v1.endpoints.audit_endpoints import router as audit_router
from src.api.v1.endpoints.auth_endpoints import router as auth_router
from src.api.v1.endpoints.coa_endpoints import router as coa_router
from src.api.v1.endpoints.mrn_endpoints import router as mrn_router
from src.api.v1.endpoints.oos_endpoints import router as oos_router
from src.api.v1.endpoints.product_endpoints import router as product_router
from src.api.v1.endpoints.resource_endpoints import router as resource_router
from src.api.v1.endpoints.result_endpoints import router as result_router
from src.api.v1.endpoints.sample_endpoints import router as sample_router
from src.api.v1.endpoints.sap_endpoints import router as sap_router
from src.api.v1.endpoints.specification_endpoints import router as specification_router
from src.api.v1.endpoints.stability_endpoints import router as stability_router
from src.api.v1.endpoints.test_endpoints import router as test_router
from src.api.v1.endpoints.test_template_endpoints import router as test_template_router
from src.api.v1.endpoints.trf_endpoints import router as trf_router
from src.api.v1.endpoints.user_endpoints import router as user_router
from src.api.v1.endpoints.worksheet_endpoints import router as worksheet_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(auth_router)
api_v1_router.include_router(user_router)
api_v1_router.include_router(product_router)
api_v1_router.include_router(test_router)
api_v1_router.include_router(specification_router)
api_v1_router.include_router(sample_router)
api_v1_router.include_router(result_router)
api_v1_router.include_router(oos_router)
api_v1_router.include_router(resource_router)
api_v1_router.include_router(sap_router)
api_v1_router.include_router(audit_router)
api_v1_router.include_router(mrn_router)
api_v1_router.include_router(stability_router)
api_v1_router.include_router(trf_router)
api_v1_router.include_router(test_template_router)
#  Carries no prefix of its own: worksheets are reached both through their TRF
#  test line (`/trf/test-lines/{id}/worksheet`, matching the shape trf_router
#  already uses for result entry) and by their own id (`/worksheets/{id}`).
api_v1_router.include_router(worksheet_router)
#  Also unprefixed: attachments hang off both `/trf/...` and `/attachments/...`.
api_v1_router.include_router(attachment_router)
api_v1_router.include_router(coa_router)
api_v1_router.include_router(attachment_router)
