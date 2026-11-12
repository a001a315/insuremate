import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { AuthProvider } from "@/context/AuthContext";
import { ToastProvider } from "@/context/ToastContext";

export const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

/** Route fetch calls by URL substring. Unmatched calls return an empty list. */
export function mockApi(routes: Record<string, unknown | ((init?: RequestInit) => Response)>) {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    for (const [k, v] of Object.entries(routes)) if (url.includes(k)) return typeof v === "function" ? (v as (i?: RequestInit) => Response)(init) : json(v);
    return json([]);
  });
}

export function renderWithProviders(ui: ReactElement, route = "/") {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}><ToastProvider><AuthProvider><MemoryRouter initialEntries={[route]}>{ui}</MemoryRouter></AuthProvider></ToastProvider></QueryClientProvider>);
}
