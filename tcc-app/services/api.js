// URL base da API vem de EXPO_PUBLIC_API_URL (definida em .env na raiz do app).
// Em dev, copie `.env.example` para `.env` e ajuste o IP do backend.
const API_URL =
  process.env.EXPO_PUBLIC_API_URL ||
  "http://192.168.5.121:8000";

import { storage } from "./storage";

async function getAuthHeaders(contentType = "application/json") {
  const token = await storage.getItem("access_token");
  const headers = {
    Accept: "application/json",
  };

  if (contentType) {
    headers["Content-Type"] = contentType;
  }

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

async function clearSession() {
  await storage.removeItem("access_token");
  await storage.removeItem("refresh_token");
  await storage.removeItem("user_role");
  await storage.removeItem("user_id");
  await storage.removeItem("user_name");
  await storage.removeItem("user_email");
  await storage.removeItem("user_ra");
  await storage.removeItem("primeiro_acesso");
  await storage.removeItem("face_cadastrada");
}

// Evita múltiplas chamadas de refresh concorrentes
let refreshPromise = null;

async function tryRefreshToken() {
  if (refreshPromise) return refreshPromise;

  refreshPromise = (async () => {
    const refresh = await storage.getItem("refresh_token");
    if (!refresh) return null;

    try {
      const response = await fetch(`${API_URL}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ refresh_token: refresh }),
      });
      if (!response.ok) return null;
      const data = await response.json();
      if (data.access_token && data.refresh_token) {
        await storage.setItem("access_token", data.access_token);
        await storage.setItem("refresh_token", data.refresh_token);
        return data.access_token;
      }
      return null;
    } catch {
      return null;
    }
  })();

  try {
    return await refreshPromise;
  } finally {
    refreshPromise = null;
  }
}

async function authFetch(endpoint, init, contentType) {
  const headers = await getAuthHeaders(contentType);
  const merged = { ...init, headers: { ...headers, ...(init.headers || {}) } };
  let response = await fetch(`${API_URL}${endpoint}`, merged);

  if (response.status === 401) {
    const newToken = await tryRefreshToken();
    if (newToken) {
      merged.headers["Authorization"] = `Bearer ${newToken}`;
      response = await fetch(`${API_URL}${endpoint}`, merged);
    } else {
      await clearSession();
    }
  }
  return response;
}

export async function apiGet(endpoint) {
  const response = await authFetch(endpoint, { method: "GET" });
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || `Erro HTTP ${response.status}`);
  return data;
}

export async function apiPost(endpoint, body) {
  const response = await authFetch(
    endpoint,
    { method: "POST", body: JSON.stringify(body) },
    "application/json"
  );
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || `Erro HTTP ${response.status}`);
  return data;
}

export async function apiPostFormData(endpoint, formData) {
  // Para FormData, deixamos o fetch definir o Content-Type com o boundary.
  const token = await storage.getItem("access_token");
  const headers = { Accept: "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  let response = await fetch(`${API_URL}${endpoint}`, {
    method: "POST",
    headers,
    body: formData,
  });

  if (response.status === 401) {
    const newToken = await tryRefreshToken();
    if (newToken) {
      headers["Authorization"] = `Bearer ${newToken}`;
      response = await fetch(`${API_URL}${endpoint}`, {
        method: "POST",
        headers,
        body: formData,
      });
    } else {
      await clearSession();
    }
  }

  const data = await response.json();
  if (!response.ok) {
    let errorMsg = `Erro HTTP ${response.status}`;
    if (data.detail) {
      if (Array.isArray(data.detail)) {
        errorMsg = data.detail.map(err => `${err.loc.join('.')}: ${err.msg}`).join('\n');
      } else {
        errorMsg = data.detail;
      }
    }
    throw new Error(errorMsg);
  }
  return data;
}

export async function loginRequest(email, senha) {
  const formData = new URLSearchParams();
  formData.append("username", email);
  formData.append("password", senha);

  const response = await fetch(`${API_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: formData.toString(),
  });

  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "Erro ao fazer login");
  return data;
}

export async function logoutRequest() {
  const refresh = await storage.getItem("refresh_token");
  if (refresh) {
    try {
      await authFetch(
        "/auth/logout",
        { method: "POST", body: JSON.stringify({ refresh_token: refresh }) },
        "application/json"
      );
    } catch {
      // ignorado: limpeza local é autoritativa
    }
  }
  await clearSession();
}
