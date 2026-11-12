import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AppLayout } from "@/components/layout/AppLayout";
import { AssistantPage } from "@/pages/AssistantPage";
import { ClaimsPage } from "@/pages/ClaimsPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { HospitalPage } from "@/pages/HospitalPage";
import { PatientsPage } from "@/pages/PatientsPage";
import { PoliciesPage } from "@/pages/PoliciesPage";
import { json, mockApi, renderWithProviders } from "@/test-utils";

afterEach(() => { vi.restoreAllMocks(); localStorage.clear(); });
const user = { id: "1", email: "a@example.com", full_name: "Asha Demo", is_demo: false, hospital_name: "Test City Hospital", hospital_city: null };

describe("error and empty states", () => {
  it("shows the server error when claims fail to load", async () => {
    mockApi({ "/claims": () => json({ detail: "Database unavailable" }, 500) });
    renderWithProviders(<ClaimsPage />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Database unavailable");
  });
  it("shows an empty state with a call to action when there are no policies", async () => {
    mockApi({ "/policies": [] });
    renderWithProviders(<PoliciesPage />);
    expect(await screen.findByText("No policies yet")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /add a policy/i })).toBeInTheDocument();
  });
  it("lists policies with masked numbers", async () => {
    mockApi({ "/policies": [{ id: "p1", patient_id: "pt1", patient_name: "Asha Verma", tpa_name: null, network_status: "empanelled_cashless", name: "Shield", insurer: "Sample", masked_policy_number: "•••••4567", policy_type: "individual", sum_insured: 1000000, premium_amount: 20000, premium_frequency: "annual", expiry_date: "2027-03-31", renewal_date: null, status: "active" }] });
    renderWithProviders(<PoliciesPage />);
    expect(await screen.findByText("•••••4567")).toBeInTheDocument();
    expect(screen.getByText("₹10,00,000")).toBeInTheDocument();
    expect(screen.getByText("31 Mar 2027")).toBeInTheDocument();
    expect(screen.getByText("Asha Verma")).toBeInTheDocument();
    expect(screen.getByText("Cashless at this hospital")).toBeInTheDocument();
  });
  it("tells the user when the backend is unreachable", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("fail"));
    renderWithProviders(<DashboardPage />);
    expect(await screen.findByText(/cannot reach the server/i)).toBeInTheDocument();
  });
});

describe("dashboard", () => {
  const base = { summary: { patients: 4, active_policies: 5, expiring_policies: 1, pending_claims: 2, rejected_claims: 1, cleared_claims: 1, amount_pending: 250000, amount_approved: 37800, amount_pending_display: "₹2,50,000", amount_approved_display: "₹37,800", empanelled_insurers: 3 }, claims_by_status: [{ status: "rejected", count: 1 }], expiring: [], recent_claims: [], recent_documents: [], activity: [], insights: [] };
  it("shows hospital summary tiles and only the insights the API returned", async () => {
    mockApi({ "/dashboard": { ...base, insights: [{ kind: "network", text: "1 active policy from Nowhere is not in your empanelment list." }],
      expiring: [{ id: "p1", name: "Shield", insurer: "Sample", patient_id: "pt1", patient_name: "Asha Verma", expiry_date: "2026-12-01", days_left: 20, network_status: "empanelled_cashless" }] } });
    renderWithProviders(<DashboardPage />);
    expect(await screen.findByText("₹2,50,000 claimed")).toBeInTheDocument();
    expect(screen.getByText("₹37,800 approved")).toBeInTheDocument();
    expect(screen.getByText("1 active policy from Nowhere is not in your empanelment list.")).toBeInTheDocument();
    expect(screen.getByText("Asha Verma")).toBeInTheDocument();
  });
  it("shows no fabricated insights when there are none", async () => {
    mockApi({ "/dashboard": base });
    renderWithProviders(<DashboardPage />);
    expect(await screen.findByText(/Nothing needs attention/)).toBeInTheDocument();
  });
});

describe("patients", () => {
  it("lists patients with insurance state and claim clearance", async () => {
    mockApi({ "/patients": [{ id: "pt1", full_name: "Asha Verma", mrn: "MRN-1", date_of_birth: null, gender: null, phone: null, notes: null, created_at: "",
      active_policies: 1, open_claims: 1, latest_claim_status: "rejected", latest_clearance: "rejected", insurance_state: "expiring_soon" }] });
    renderWithProviders(<PatientsPage />);
    expect(await screen.findByRole("link", { name: "Asha Verma" })).toHaveAttribute("href", "/patients/pt1");
    expect(screen.getByText("Expiring soon")).toBeInTheDocument();
    expect(screen.getByText("Rejected", { selector: "span.rounded-full" })).toBeInTheDocument();
  });
  it("shows an empty state with a call to action", async () => {
    mockApi({ "/patients": [] });
    renderWithProviders(<PatientsPage />);
    expect(await screen.findByText("No patients yet")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /register your first patient/i })).toBeInTheDocument();
  });
});

describe("hospital setup", () => {
  it("lists empanelled insurers and flags a lapsed empanelment", async () => {
    mockApi({ "/hospital/empanelments": [{ id: "e1", insurer: "Sample Mutual", tpa_name: "Demo TPA", cashless_enabled: true, valid_until: "2020-01-01", notes: null },
      { id: "e2", insurer: "Imaginary Shield", tpa_name: null, cashless_enabled: false, valid_until: null, notes: null }] });
    renderWithProviders(<HospitalPage />);
    expect(await screen.findByText("Sample Mutual")).toBeInTheDocument();
    expect(screen.getByText(/\(lapsed\)/)).toBeInTheDocument();
    expect(screen.getByText("Reimbursement only")).toBeInTheDocument();
  });
});

describe("navigation", () => {
  it("navigates between sections from the sidebar", async () => {
    localStorage.setItem("insuremate.token", "t");
    mockApi({ "/auth/me": user, "/notifications": { unread: 0, items: [] }, "/policies": [] });
    renderWithProviders(<Routes><Route element={<AppLayout />}><Route index element={<p>overview page</p>} /><Route path="policies" element={<PoliciesPage />} /></Route></Routes>);
    expect(await screen.findByText("overview page")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("link", { name: "Policies" }));
    expect(await screen.findByRole("heading", { name: "Policies" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Policies" })).toHaveClass("text-primary");
  });
});

describe("assistant", () => {
  it("shows suggested questions, and renders citations with document name and page", async () => {
    mockApi({ "/patients": [], "/policies": [{ id: "p1", name: "Shield" }], "/chat/conversations/c1/messages": [
      { id: "m1", role: "user", content: "Is room rent capped?", citations: [], created_at: "" },
      { id: "m2", role: "assistant", content: "**Policy:** Shield\n\nRoom rent is capped at 1% (p. 3).", created_at: "",
        citations: [{ type: "document", document_name: "policy.pdf", page_number: 3, excerpt: "Room rent is capped at 1 percent", score: 0.8 }] }],
      "/chat/conversations": [{ id: "c1", title: "Is room rent capped?", policy_id: null, updated_at: "" }] });
    renderWithProviders(<AssistantPage />);
    expect(await screen.findByText("Which claims were rejected?")).toBeInTheDocument();
    const history = await screen.findByLabelText("Conversation history");
    await userEvent.click(await within(history).findByRole("button", { name: "Is room rent capped?" }));
    const cite = await screen.findByText("policy.pdf");
    expect(cite.closest("button")).toHaveTextContent("page 3");
    await userEvent.click(cite);
    expect(await screen.findByText(/Room rent is capped at 1 percent…/)).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("button", { name: /new conversation/i })).toBeInTheDocument());
  });
});
