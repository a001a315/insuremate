import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AppLayout } from "@/components/layout/AppLayout";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import { AuthPage } from "@/pages/AuthPage";
import { ToastProvider } from "@/context/ToastContext";
import { AssistantPage } from "@/pages/AssistantPage";
import { ClaimDetailPage } from "@/pages/ClaimDetailPage";
import { ClaimsPage } from "@/pages/ClaimsPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { DocumentsPage } from "@/pages/DocumentsPage";
import { HospitalPage } from "@/pages/HospitalPage";
import { PatientDetailPage } from "@/pages/PatientDetailPage";
import { PatientsPage } from "@/pages/PatientsPage";
import { PoliciesPage } from "@/pages/PoliciesPage";
import { PolicyDetailPage } from "@/pages/PolicyDetailPage";
import { RecordsPage } from "@/pages/RecordsPage";
import { RemindersPage } from "@/pages/RemindersPage";
import { SettingsPage } from "@/pages/SettingsPage";

const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } } });

function Protected() {
  const { user, loading } = useAuth();
  if (loading) return <div className="p-6 text-sm text-muted">Loading…</div>;
  return user ? <AppLayout /> : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ToastProvider><AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<AuthPage mode="login" />} />
            <Route path="/register" element={<AuthPage mode="register" />} />
            <Route element={<Protected />}>
              <Route index element={<DashboardPage />} />
              <Route path="patients" element={<PatientsPage />} />
              <Route path="patients/:id" element={<PatientDetailPage />} />
              <Route path="hospital" element={<HospitalPage />} />
              <Route path="policies" element={<PoliciesPage />} />
              <Route path="policies/:id" element={<PolicyDetailPage />} />
              <Route path="claims" element={<ClaimsPage />} />
              <Route path="claims/:id" element={<ClaimDetailPage />} />
              <Route path="records" element={<RecordsPage />} />
              <Route path="documents" element={<DocumentsPage />} />
              <Route path="assistant" element={<AssistantPage />} />
              <Route path="reminders" element={<RemindersPage />} />
              <Route path="settings" element={<SettingsPage />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider></ToastProvider>
    </QueryClientProvider>
  );
}
