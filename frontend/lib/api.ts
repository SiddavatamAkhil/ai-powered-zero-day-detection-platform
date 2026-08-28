/**
 * Thin typed fetch wrapper.
 *
 * Centralizes:
 * - API base URL
 * - Authorization header injection
 * - Automatic refresh-and-retry on 401
 * - Login
 *
 * Browser runs on localhost, so Docker's internal hostname
 * "backend" must NOT be used by browser requests.
 */

const DEFAULT_PROD_URL = "https://ai-powered-zero-day-detection-platform.onrender.com/api/v1";

export function getApiUrl(): string {
  const envUrl = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (envUrl) {
    return envUrl.replace(/\/$/, "");
  }
  if (typeof window !== "undefined" && window.location.hostname !== "localhost" && window.location.hostname !== "127.0.0.1") {
    return DEFAULT_PROD_URL;
  }
  return "http://localhost:8000/api/v1";
}

export const API_URL = getApiUrl();

/**
 * Dedicated health check helper.
 * Requests root /health endpoint (e.g. https://domain.com/health),
 * correctly stripping /api/v1 prefix from the base URL.
 */
export async function checkBackendHealth(): Promise<boolean> {
  const baseUrl = getApiUrl();
  const rootHealthUrl = baseUrl.replace(/\/api\/v1\/?$/, "") + "/health";
  try {
    const res = await fetch(rootHealthUrl, { method: "GET", cache: "no-store" });
    return res.ok;
  } catch {
    return false;
  }
}

/* ---------------------------------------------------------
   Token types
--------------------------------------------------------- */

interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type?: string;
}

/* ---------------------------------------------------------
   Token storage
--------------------------------------------------------- */

function getStoredTokens(): AuthTokens | null {
  if (typeof window === "undefined") {
    return null;
  }

  const raw = window.localStorage.getItem("zeroday_tokens");

  if (!raw) {
    return null;
  }

  try {
    return JSON.parse(raw) as AuthTokens;
  } catch {
    window.localStorage.removeItem("zeroday_tokens");
    return null;
  }
}

function storeTokens(tokens: AuthTokens): void {
  if (typeof window === "undefined") {
    return;
  }

  window.localStorage.setItem(
    "zeroday_tokens",
    JSON.stringify(tokens)
  );
}

export function clearTokens(): void {
  if (typeof window !== "undefined") {
    window.localStorage.removeItem("zeroday_tokens");
  }
}

/* ---------------------------------------------------------
   Refresh access token
--------------------------------------------------------- */

async function refreshAccessToken(): Promise<string | null> {
  const tokens = getStoredTokens();

  if (!tokens?.refresh_token) {
    return null;
  }

  try {
    const response = await fetch(`${API_URL}/auth/refresh`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        refresh_token: tokens.refresh_token,
      }),
    });

    if (!response.ok) {
      clearTokens();
      return null;
    }

    const newTokens = (await response.json()) as AuthTokens;

    storeTokens(newTokens);

    return newTokens.access_token;
  } catch {
    clearTokens();
    return null;
  }
}

/* ---------------------------------------------------------
   Generic API fetch
--------------------------------------------------------- */

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const tokens = getStoredTokens();
  const baseUrl = getApiUrl();
  const fullUrl = `${baseUrl}${path}`;
  const headers = new Headers(options.headers);

  if (tokens?.access_token) {
    headers.set("Authorization", `Bearer ${tokens.access_token}`);
  }

  if (!(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  let response: Response;

  try {
    response = await fetch(fullUrl, {
      ...options,
      headers,
    });
  } catch (error) {
    console.error(`[API Error] Request failed for ${fullUrl}:`, error);
    throw new Error(
      `Unable to reach backend at ${baseUrl}. Backend may be warming up or offline.`
    );
  }

  if (response.status === 401) {
    const newAccessToken = await refreshAccessToken();

    if (newAccessToken) {
      headers.set("Authorization", `Bearer ${newAccessToken}`);

      try {
        response = await fetch(fullUrl, {
          ...options,
          headers,
        });
      } catch (err) {
        console.error(`[API Error] Retry failed for ${fullUrl}:`, err);
        throw new Error(`Unable to reach backend at ${API_URL}`);
      }
    } else {
      if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
        window.location.href = "/login";
      }
    }
  }

  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(body?.detail ?? `Request to ${path} failed (HTTP ${response.status})`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

/* ---------------------------------------------------------
   Generic authenticated blob download
--------------------------------------------------------- */

export async function downloadBlob(
  path: string,
  options: RequestInit = {}
): Promise<Blob> {
  const tokens = getStoredTokens();
  const headers = new Headers(options.headers);
  const fullUrl = `${API_URL}${path}`;

  if (tokens?.access_token) {
    headers.set("Authorization", `Bearer ${tokens.access_token}`);
  }

  let response: Response;

  try {
    response = await fetch(fullUrl, {
      ...options,
      headers,
    });
  } catch (error) {
    console.error(`[API Error] Request failed for ${fullUrl}:`, error);
    throw new Error(
      `Unable to reach backend at ${API_URL}. Backend may be warming up or offline.`
    );
  }

  if (response.status === 401) {
    const newAccessToken = await refreshAccessToken();
    if (newAccessToken) {
      headers.set("Authorization", `Bearer ${newAccessToken}`);
      try {
        response = await fetch(fullUrl, { ...options, headers });
      } catch (err) {
        throw new Error(`Unable to reach backend at ${API_URL}`);
      }
    } else {
      if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
        window.location.href = "/login";
      }
    }
  }

  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(body?.detail ?? `Download from ${path} failed (HTTP ${response.status})`);
  }

  return response.blob();
}

/* ---------------------------------------------------------
   Login
--------------------------------------------------------- */

export async function login(
  email: string,
  password: string
): Promise<AuthTokens> {
  const targetUrl = `${API_URL}/auth/login`;
  console.log(`[API] Login request to: ${targetUrl}`);

  let response: Response;

  try {
    response = await fetch(targetUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        email,
        password,
      }),
    });
  } catch (error) {
    console.error(`[API Error] Network failure connecting to ${targetUrl}:`, error);
    throw new Error(
      `Unable to reach backend at ${API_URL}. If using Render free tier, the backend may be spinning up (~45s cold start). Please wait 30 seconds and try again.`
    );
  }

  console.log(`[API Response] Status: ${response.status} ${response.statusText} from ${targetUrl}`);

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail = body?.detail;

    if (response.status === 401) {
      throw new Error(detail ?? "Invalid email or password.");
    } else if (response.status === 404) {
      throw new Error(`Endpoint not found (404) at ${targetUrl}. Please verify API URL configuration.`);
    } else if (response.status >= 500) {
      throw new Error(
        `Backend database/server error (HTTP ${response.status}). ${detail ? `Detail: ${detail}` : 'Please check backend logs on Render.'}`
      );
    }

    throw new Error(detail ?? `Login request failed with status ${response.status}`);
  }

  const tokens = (await response.json()) as AuthTokens;
  storeTokens(tokens);
  return tokens;
}

/* ---------------------------------------------------------
   Dataset
--------------------------------------------------------- */

export interface Dataset {
  id: string;
  name: string;
  status: string;
  num_rows: number | null;
  num_features: number | null;
  label_column: string;

  classes: {
    class_name: string;
    sample_count: number;
    split: "known" | "unknown_holdout";
    is_benign: boolean;
  }[];
}

/* ---------------------------------------------------------
   ML Model
--------------------------------------------------------- */

export interface MLModelResult {
  id: string;
  architecture: string;

  accuracy: number | null;
  precision: number | null;
  recall: number | null;
  f1: number | null;
  mcc: number | null;
  roc_auc: number | null;

  false_positive_rate: number | null;
  unknown_attack_recall: number | null;

  training_time_seconds: number | null;
  inference_time_ms_per_sample: number | null;
}

/* ---------------------------------------------------------
   API methods
--------------------------------------------------------- */

export const api = {
  /*
   * Dataset APIs
   */

  listDatasets: () =>
    apiFetch<Dataset[]>("/datasets"),

  getDataset: (id: string) =>
    apiFetch<Dataset>(`/datasets/${id}`),

  deleteDataset: (id: string) =>
    apiFetch<void>(`/datasets/${id}`, { method: "DELETE" }),

  /*
   * Model comparison
   */

  compareModels: (datasetId: string) =>
    apiFetch<MLModelResult[]>(
      `/models/compare/${datasetId}`
    ),

  /*
   * Training
   */

  startTraining: (payload: {
    dataset_id: string;
    architecture: string;
    epochs: number;
  }) =>
    apiFetch("/training/runs", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  /*
   * Current logged-in user
   */

  me: () =>
    apiFetch<{
      email: string;
      full_name: string;
      role: string;
      is_active?: boolean;
      id?: string;
    }>("/auth/me"),

  checkHealth: checkBackendHealth,
};