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

const configuredApiUrl = process.env.NEXT_PUBLIC_API_URL?.trim();

const API_URL =
  process.env.NEXT_PUBLIC_API_URL?.trim().replace(/\/$/, "") ||
  "http://localhost:8000/api/v1";

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

  const headers = new Headers(options.headers);

  /*
   * Add JWT access token when available.
   */
  if (tokens?.access_token) {
    headers.set(
      "Authorization",
      `Bearer ${tokens.access_token}`
    );
  }

  /*
   * JSON content type for normal requests.
   * Do not set it for FormData uploads.
   */
  if (!(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  let response: Response;

  try {
    response = await fetch(`${API_URL}${path}`, {
      ...options,
      headers,
    });
  } catch (error) {
    console.error("API connection failed:", error);
    console.error("API URL:", API_URL);

    throw new Error(
      `Unable to connect to backend at ${API_URL}`
    );
  }

  /*
   * If access token expired, refresh it once
   * and retry the original request.
   */
  if (response.status === 401) {
    const newAccessToken = await refreshAccessToken();

    if (newAccessToken) {
      headers.set(
        "Authorization",
        `Bearer ${newAccessToken}`
      );

      try {
        response = await fetch(`${API_URL}${path}`, {
          ...options,
          headers,
        });
      } catch {
        throw new Error(
          `Unable to connect to backend at ${API_URL}`
        );
      }
    }
  }

  /*
   * Handle API errors.
   */
  if (!response.ok) {
    const body = await response
      .json()
      .catch(() => ({
        detail: response.statusText,
      }));

    throw new Error(
      body?.detail ?? "Request failed"
    );
  }

  /*
   * 204 No Content.
   */
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

/* ---------------------------------------------------------
   Login
--------------------------------------------------------- */

export async function login(
  email: string,
  password: string
): Promise<AuthTokens> {
  let response: Response;

  try {
    response = await fetch(`${API_URL}/auth/login`, {
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
    console.error("Login connection error:", error);
    console.error("API URL:", API_URL);

    throw new Error(
      `Failed to connect to backend at ${API_URL}`
    );
  }

  if (!response.ok) {
    const body = await response
      .json()
      .catch(() => null);

    throw new Error(
      body?.detail ?? "Invalid email or password."
    );
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
};