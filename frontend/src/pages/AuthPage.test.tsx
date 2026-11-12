import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { mockApi, renderWithProviders } from "@/test-utils";
import { AuthPage } from "./AuthPage";
import { AppLayout } from "@/components/layout/AppLayout";

function renderAuth(mode: "login" | "register") {
  return renderWithProviders(
    <Routes>
      <Route path="/auth" element={<AuthPage mode={mode} />} />
      <Route path="/" element={<AppLayout />}><Route index element={<p>home</p>} /></Route>
    </Routes>, "/auth");
}

afterEach(() => { vi.restoreAllMocks(); localStorage.clear(); });

describe("AuthPage", () => {
  it("validates fields before calling the API", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    renderAuth("register");
    await userEvent.click(screen.getByRole("button", { name: /register hospital/i }));
    expect(await screen.findByText("Your name is required")).toBeInTheDocument();
    expect(screen.getByText("Hospital name is required")).toBeInTheDocument();
    expect(screen.getByText("Enter a valid email address")).toBeInTheDocument();
    expect(screen.getByText("Use at least 8 characters")).toBeInTheDocument();
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("shows server errors", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ detail: "Incorrect email or password." }), { status: 401 }));
    renderAuth("login");
    await userEvent.type(screen.getByLabelText("Email"), "a@example.com");
    await userEvent.type(screen.getByLabelText("Password"), "whatever1");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Incorrect email or password.");
  });

  it("shows a friendly error when the backend is unreachable", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("fail"));
    renderAuth("login");
    await userEvent.type(screen.getByLabelText("Email"), "a@example.com");
    await userEvent.type(screen.getByLabelText("Password"), "whatever1");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));
    expect(await screen.findByText(/cannot reach the server/i)).toBeInTheDocument();
  });

  it("logs in and navigates to the app shell with all nav items", async () => {
    const user = { id: "1", email: "a@example.com", full_name: "Asha Demo", is_demo: false, hospital_name: "Test City Hospital", hospital_city: null };
    mockApi({ "/auth/login": { access_token: "t", token_type: "bearer", user }, "/notifications": { unread: 0, items: [] } });
    renderAuth("login");
    await userEvent.type(screen.getByLabelText("Email"), "a@example.com");
    await userEvent.type(screen.getByLabelText("Password"), "whatever1");
    await userEvent.click(screen.getByRole("button", { name: /sign in/i }));
    await waitFor(() => expect(screen.getByText("home")).toBeInTheDocument());
    for (const label of ["Overview", "Patients", "Policies", "Claims", "Medical Records", "Documents", "AI Assistant", "Reminders", "Hospital Setup", "Settings"])
      expect(screen.getByRole("link", { name: label })).toBeInTheDocument();
    expect(screen.getByText("Test City Hospital")).toBeInTheDocument();
    expect(localStorage.getItem("insuremate.token")).toBe("t");
  });
});
