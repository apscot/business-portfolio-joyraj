import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "../App";
import { AuthProvider } from "../auth";
import Pager from "./Pager";
import Table from "./Table";

function json(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

function renderApp(path = "/") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AuthProvider>
        <App />
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("App routing and login", () => {
  beforeEach(() => {
    const store = new Map<string, string>();
    vi.stubGlobal("localStorage", {
      getItem: (k: string) => store.get(k) ?? null,
      setItem: (k: string, v: string) => void store.set(k, v),
      removeItem: (k: string) => void store.delete(k),
      clear: () => store.clear(),
    });
  });
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("redirects unauthenticated users to the login page", async () => {
    vi.stubGlobal("fetch", vi.fn());
    renderApp("/pnl");
    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeTruthy();
  });

  it("validates fields inline without calling the backend", async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    renderApp("/login");
    await userEvent.type(screen.getByLabelText("Email"), "nope");
    await userEvent.type(screen.getByLabelText("Password"), "short");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(screen.getByText("Enter a valid email address.")).toBeTruthy();
    expect(screen.getByText("Password must be at least 8 characters.")).toBeTruthy();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("shows the server error inline on bad credentials", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(json(401, { detail: "Invalid email or password" })));
    renderApp("/login");
    await userEvent.type(screen.getByLabelText("Email"), "a@b.com");
    await userEvent.type(screen.getByLabelText("Password"), "password123");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect((await screen.findByRole("alert")).textContent).toBe("Invalid email or password");
  });

  it("signs in, stores the token and shows the layout", async () => {
    const fetchMock = vi.fn(async (url: string) => {
      if (url === "/api/auth/login") return json(200, { access_token: "tok" });
      if (url === "/api/auth/me") return json(200, { id: 1, email: "a@b.com" });
      if (url.startsWith("/api/fy")) return json(200, ["2025-26"]);
      return json(404, {});
    });
    vi.stubGlobal("fetch", fetchMock);
    renderApp("/login");
    await userEvent.type(screen.getByLabelText("Email"), "a@b.com");
    await userEvent.type(screen.getByLabelText("Password"), "password123");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("heading", { name: "Home" })).toBeTruthy();
    expect(screen.getByText("a@b.com")).toBeTruthy();
    expect(localStorage.getItem("fo_token")).toBe("tok");
    await waitFor(() => expect(screen.getByRole("option", { name: "2025-26" })).toBeTruthy());
    await userEvent.click(screen.getByRole("button", { name: "Log out" }));
    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeTruthy();
  });

  it("toggles to create account and registers", async () => {
    const fetchMock = vi.fn(async (url: string) => {
      if (url === "/api/auth/register") return json(201, { access_token: "tok2" });
      if (url === "/api/auth/me") return json(200, { id: 2, email: "new@b.com" });
      if (url.startsWith("/api/summary")) return json(200, { fy: "2025-26", invested: "0", interest: "0", total: "0", holdings: "0", series: [] });
      return json(200, []);
    });
    vi.stubGlobal("fetch", fetchMock);
    renderApp("/login");
    await userEvent.click(screen.getByRole("button", { name: "Create account" }));
    expect(screen.getByRole("heading", { name: "Create account" })).toBeTruthy();
    await userEvent.type(screen.getByLabelText("Email"), "new@b.com");
    await userEvent.type(screen.getByLabelText("Password"), "password123");
    await userEvent.click(screen.getAllByRole("button", { name: "Create account" })[0]);
    expect(await screen.findByRole("heading", { name: "Home" })).toBeTruthy();
  });
});

describe("Table and Pager", () => {
  afterEach(cleanup);

  it("shows an empty state for no rows", () => {
    render(<Table columns={[{ key: "a", header: "A", render: (r: { a: string }) => r.a }]} rows={[]} rowKey={(r) => r.a} emptyMessage="Nothing" />);
    expect(screen.getByText("Nothing")).toBeTruthy();
  });

  it("paginates", async () => {
    const onChange = vi.fn();
    render(<Pager page={2} pageSize={15} total={40} onChange={onChange} />);
    expect(screen.getByText("16–30 of 40")).toBeTruthy();
    await userEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(onChange).toHaveBeenCalledWith(3);
    await userEvent.click(screen.getByRole("button", { name: "Previous" }));
    expect(onChange).toHaveBeenCalledWith(1);
  });
});
