/**
 * Application router — public login route + private module routes under MainLayout.
 */
import { Navigate, Route, Routes } from 'react-router-dom';
import { MainLayout } from '@app/layouts/MainLayout';
import { PrivateRoute } from './PrivateRoute';
import { LoginPage } from '@features/authentication';
import { DashboardPage } from '@features/dashboard/pages/DashboardPage';
import {
  OOSPage,
  ProductsPage,
  SampleDetailPage,
  SamplesPage,
  SpecificationsPage,
  TestsPage,
} from '@features/sample-management';
import {
  ChemicalsPage,
  ColumnsPage,
  InstrumentsPage,
  StandardsPage,
  VolumetricPage,
} from '@features/resource-management';
import { SAPIntegrationPage } from '@features/sap-integration/pages/SAPIntegrationPage';
import { UsersPage } from '@features/user-management/pages/UsersPage';
import { AuditPage } from '@features/audit/pages/AuditPage';
import { MaterialQueuePage, MRNDetailPage, MyMRNsPage } from '@features/mrn';
import { PrintATRPage, TRFDetailPage, TRFListPage } from '@features/trf';
import { TemplateDetailPage, TemplateListPage } from '@features/test-templates';
import { CoaListPage, PrintCoaPage } from '@features/coa';
import { PrintProtocolPage, PrintReportPage, ProtocolDetailPage, ProtocolsPage } from '@features/stability';

export const AppRouter = () => (
  <Routes>
    <Route path="/login" element={<LoginPage />} />

    <Route element={<PrivateRoute />}>
      <Route path="/stability/:id/print" element={<PrintProtocolPage />} />
      <Route path="/stability/reports/:id/print" element={<PrintReportPage />} />
      <Route path="/trf/:id/atr/print" element={<PrintATRPage />} />
      {/* Outside MainLayout so the printed page carries no sidebar or topbar. */}
      <Route path="/coa/:id/print" element={<PrintCoaPage />} />

      <Route element={<MainLayout />}>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<DashboardPage />} />

        <Route path="/samples" element={<SamplesPage />} />
        <Route path="/samples/:id" element={<SampleDetailPage />} />
        <Route path="/products" element={<ProductsPage />} />
        <Route path="/tests" element={<TestsPage />} />
        <Route path="/specifications" element={<SpecificationsPage />} />
        <Route path="/oos" element={<OOSPage />} />

        <Route path="/instruments" element={<InstrumentsPage />} />
        <Route path="/stability" element={<ProtocolsPage />} />
        <Route path="/stability/:id" element={<ProtocolDetailPage />} />
        <Route path="/chemicals" element={<ChemicalsPage />} />
        <Route path="/standards" element={<StandardsPage />} />
        <Route path="/columns" element={<ColumnsPage />} />
        <Route path="/volumetric" element={<VolumetricPage />} />

        <Route path="/mrn/queue" element={<MaterialQueuePage />} />
        <Route path="/mrn" element={<MyMRNsPage />} />
        <Route path="/mrn/:id" element={<MRNDetailPage />} />

        <Route path="/trf" element={<TRFListPage />} />
        <Route path="/trf/:id" element={<TRFDetailPage />} />

        <Route path="/test-templates" element={<TemplateListPage />} />
        <Route path="/test-templates/:id" element={<TemplateDetailPage />} />

        <Route path="/coa" element={<CoaListPage />} />

        <Route path="/sap" element={<SAPIntegrationPage />} />
        <Route path="/users" element={<UsersPage />} />
        <Route path="/audit" element={<AuditPage />} />
      </Route>
    </Route>

    <Route path="*" element={<Navigate to="/dashboard" replace />} />
  </Routes>
);
