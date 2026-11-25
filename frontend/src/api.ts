// Single place that talks to the backend. Pages must call the backend only through this module.

const BASE = "/api";
const TOKEN_KEY = "fo_token";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string | null): void {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    // storage unavailable (private mode); the session just won't persist
  }
}

type UnauthorizedHandler = () => void;
let onUnauthorized: UnauthorizedHandler | null = null;

/** Called when an authenticated request gets 401 (expired/invalid token). */
export function setUnauthorizedHandler(handler: UnauthorizedHandler | null): void {
  onUnauthorized = handler;
}

type Query = Record<string, string | number | undefined | null>;

function withQuery(path: string, query?: Query): string {
  if (!query) return BASE + path;
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== null && value !== "") params.set(key, String(value));
  }
  const qs = params.toString();
  return BASE + path + (qs ? `?${qs}` : "");
}

function errorMessage(data: unknown, fallback: string): string {
  if (data && typeof data === "object" && "detail" in data) {
    const detail = (data as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      const msgs = detail
        .map((d) => (d && typeof d === "object" && "msg" in d ? String((d as { msg: unknown }).msg) : ""))
        .filter(Boolean);
      if (msgs.length) return msgs.join("; ");
    }
  }
  return fallback;
}

async function request<T>(method: string, path: string, opts: { query?: Query; body?: BodyInit; json?: unknown } = {}): Promise<T> {
  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;
  let body = opts.body;
  if (opts.json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(opts.json);
  }

  let res: Response;
  try {
    res = await fetch(withQuery(path, opts.query), { method, headers, body });
  } catch {
    throw new ApiError(0, "Network error. Please check your connection and try again.");
  }

  const text = await res.text();
  let data: unknown = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = null;
    }
  }

  if (!res.ok) {
    if (res.status === 401 && token && onUnauthorized) onUnauthorized();
    throw new ApiError(res.status, errorMessage(data, `Request failed (${res.status})`));
  }
  return data as T;
}

export const api = {
  get: <T>(path: string, query?: Query) => request<T>("GET", path, { query }),
  post: <T>(path: string, json?: unknown, query?: Query) => request<T>("POST", path, { json, query }),
  del: <T = void>(path: string, query?: Query) => request<T>("DELETE", path, { query }),
  upload: <T>(path: string, file: File, query?: Query) => {
    const form = new FormData();
    form.append("file", file);
    return request<T>("POST", path, { body: form, query });
  },
};

// ---- Typed shapes of the backend responses (see atlas/architecture.md) ----

export interface TokenResponse {
  access_token: string;
}

export interface User {
  id: number;
  email: string;
}

export interface TradeUploadResult {
  inserted: number;
  duplicates: number;
  invalid: { row: number; reason: string }[];
}

export async function login(email: string, password: string): Promise<string> {
  const res = await api.post<TokenResponse>("/auth/login", { email, password });
  return res.access_token;
}

export async function register(email: string, password: string): Promise<string> {
  const res = await api.post<TokenResponse>("/auth/register", { email, password });
  return res.access_token;
}

export const fetchMe = () => api.get<User>("/auth/me");
