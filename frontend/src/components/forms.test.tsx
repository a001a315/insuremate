import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ClaimForm } from "@/components/claims/ClaimForm";
import { UploadZone } from "@/components/documents/UploadZone";
import { PolicyForm } from "@/components/policies/PolicyForm";
import { json, mockApi, renderWithProviders } from "@/test-utils";
import { EligibilityPanel } from "@/components/patients/EligibilityPanel";

afterEach(() => vi.restoreAllMocks());

const PATIENTS = { "/patients": [{ id: "pt1", full_name: "Asha Verma", mrn: null }] };
async function pickPatient() {
  await screen.findByRole("option", { name: "Asha Verma" });
  await userEvent.selectOptions(screen.getByLabelText("Patient"), "pt1");
}

describe("PolicyForm", () => {
  it("shows validation errors and does not call the API", async () => {
    const spy = mockApi({});
    renderWithProviders(<PolicyForm onDone={() => {}} />);
    await userEvent.click(screen.getByRole("button", { name: /add policy/i }));
    expect(await screen.findByText("Policy name is required")).toBeInTheDocument();
    expect(screen.getByText("Choose the patient")).toBeInTheDocument();
    expect(screen.getByText("Insurance company is required")).toBeInTheDocument();
    expect(screen.getByText("Policy number is required")).toBeInTheDocument();
    expect(screen.getByText("Enter a valid amount")).toBeInTheDocument();
    expect(spy.mock.calls.filter(([u]: [RequestInfo | URL, RequestInit?]) => String(u).includes("/policies"))).toHaveLength(0);
  });

  it("rejects an expiry date before the start date", async () => {
    mockApi(PATIENTS);
    renderWithProviders(<PolicyForm onDone={() => {}} />);
    await pickPatient();
    await userEvent.type(screen.getByLabelText("Policy name"), "P");
    await userEvent.type(screen.getByLabelText("Insurance company"), "I");
    await userEvent.type(screen.getByLabelText("Policy number"), "123");
    await userEvent.type(screen.getByLabelText("Policyholder name"), "H");
    await userEvent.type(screen.getByLabelText(/Sum insured/), "100000");
    await userEvent.type(screen.getByLabelText("Start date"), "2026-05-01");
    await userEvent.type(screen.getByLabelText("Expiration date"), "2026-01-01");
    await userEvent.click(screen.getByRole("button", { name: /add policy/i }));
    expect(await screen.findByText("Expiry must be after the start date")).toBeInTheDocument();
  });

  it("submits a valid policy and reports the new id", async () => {
    const onDone = vi.fn();
    const spy = mockApi({ ...PATIENTS, "/policies": () => new Response(JSON.stringify({ id: "p1" }), { status: 201 }) });
    renderWithProviders(<PolicyForm onDone={onDone} />);
    await pickPatient();
    await userEvent.type(screen.getByLabelText("TPA name (optional)"), "Demo TPA");
    await userEvent.type(screen.getByLabelText("Policy name"), "Shield");
    await userEvent.type(screen.getByLabelText("Insurance company"), "Sample");
    await userEvent.type(screen.getByLabelText("Policy number"), "POL-1");
    await userEvent.type(screen.getByLabelText("Policyholder name"), "Asha");
    await userEvent.type(screen.getByLabelText(/Sum insured/), "500000");
    await userEvent.type(screen.getByLabelText("Name"), "Asha");
    await userEvent.click(screen.getByRole("button", { name: /add policy/i }));
    await waitFor(() => expect(onDone).toHaveBeenCalledWith("p1"));
    const body = JSON.parse(String(spy.mock.calls.find(([u, i]: [RequestInfo | URL, RequestInit?]) => String(u).endsWith("/policies") && i?.method === "POST")![1]!.body));
    expect(body.sum_insured).toBe(500000);
    expect(body.patient_id).toBe("pt1");
    expect(body.tpa_name).toBe("Demo TPA");
    expect(body.initial_waiting_days).toBe(30);
    expect(body.members).toEqual([{ name: "Asha", relationship_to_holder: "self" }]);
  });

  it("surfaces server errors", async () => {
    mockApi({ ...PATIENTS, "/policies": () => new Response(JSON.stringify({ detail: "Boom from server" }), { status: 422 }) });
    renderWithProviders(<PolicyForm onDone={() => {}} />);
    await pickPatient();
    for (const [l, v] of [["Policy name", "P"], ["Insurance company", "I"], ["Policy number", "1"], ["Policyholder name", "H"], ["Name", "H"]]) await userEvent.type(screen.getByLabelText(l), v);
    await userEvent.type(screen.getByLabelText(/Sum insured/), "5");
    await userEvent.click(screen.getByRole("button", { name: /add policy/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Boom from server");
  });
});

describe("ClaimForm", () => {
  it("requires the patient's policy and rejects discharge before hospitalization", async () => {
    mockApi({ ...PATIENTS, "/policies": [{ id: "p1", name: "Shield", insurer: "Sample" }] });
    renderWithProviders(<ClaimForm onDone={() => {}} />);
    expect(screen.getByLabelText("Policy")).toBeDisabled();   // choose a patient first
    await pickPatient();
    await userEvent.type(screen.getByLabelText("Hospitalization date"), "2026-05-10");
    await userEvent.type(screen.getByLabelText("Discharge date"), "2026-05-01");
    await userEvent.click(screen.getByRole("button", { name: /create claim/i }));
    expect(await screen.findByText("Choose a policy")).toBeInTheDocument();
    expect(screen.getByText("Discharge date cannot be before hospitalization date")).toBeInTheDocument();
  });
});

describe("EligibilityPanel", () => {
  it("shows the verdict, each check with its source, and the advisory disclaimer", async () => {
    const spy = mockApi({ "/eligibility": () => json([{ policy_id: "p1", policy_name: "Shield", insurer: "Sample", verdict: "not_eligible", verdict_label: "Not eligible based on recorded data",
      disclaimer: "Advisory pre-check. The insurer/TPA makes the final decision.",
      checks: [{ key: "network", label: "Network at this hospital", status: "warn", detail: "Sample is not in this hospital's empanelment list.", source: "hospital_setup" },
        { key: "validity", label: "Policy active on admission date", status: "fail", detail: "Policy expired on 01 Jan 2026.", source: "recorded_data" }] }]) });
    renderWithProviders(<EligibilityPanel patientId="pt1" hasPolicies />);
    await userEvent.type(screen.getByLabelText(/Planned treatment/), "knee replacement");
    await userEvent.click(screen.getByRole("button", { name: /check eligibility/i }));
    const result = await screen.findByTestId("eligibility-result");
    expect(result).toHaveTextContent("Not eligible based on recorded data");
    expect(result).toHaveTextContent("Policy expired on 01 Jan 2026.");
    expect(result).toHaveTextContent("Source: hospital empanelment setup");
    expect(result).toHaveTextContent("insurer/TPA makes the final decision");
    const call = spy.mock.calls.find(([u]: [RequestInfo | URL, RequestInit?]) => String(u).includes("/eligibility"))!;
    expect(JSON.parse(String(call[1]!.body)).treatment).toBe("knee replacement");
  });
  it("cannot run without a policy", () => {
    renderWithProviders(<EligibilityPanel patientId="pt1" hasPolicies={false} />);
    expect(screen.getByRole("button", { name: /check eligibility/i })).toBeDisabled();
  });
});

describe("UploadZone", () => {
  it("rejects unsupported file types client-side without uploading", async () => {
    const xhr = vi.spyOn(XMLHttpRequest.prototype, "send");
    renderWithProviders(<UploadZone />);
    const input = screen.getByTestId("file-input") as HTMLInputElement;
    await userEvent.upload(input, new File(["x"], "malware.exe"), { applyAccept: false });
    expect(await screen.findByText(/Unsupported type/)).toBeInTheDocument();
    expect(xhr).not.toHaveBeenCalled();
  });
});
