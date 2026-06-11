// URL base da API vem de EXPO_PUBLIC_API_URL (definida em .env na raiz do app).
// Em dev, copie `.env.example` para `.env` e ajuste o IP do backend.
const API_URL = process.env.EXPO_PUBLIC_API_URL;
if (!API_URL) throw new Error("EXPO_PUBLIC_API_URL não definida. Execute 'npm run sync-env' na pasta tcc-app antes de iniciar.");

import { storage } from "./storage";
import { friendlyErrorMessage, HTTP_STATUS_MESSAGES } from "./errorMessages";

/**
 * Normaliza o `detail` recebido do backend.
 * Backend novo: { detail: "...", error_code: "..." }
 * Backend antigo: "string"
 * Pydantic: [{ loc, msg, type }, ...]
 */
// Campos de senha tratados com mensagens dedicadas em vez do `loc: msg` cru
// do Pydantic. Quando o backend ajustar min_length/max_length, o ctx que vem
// na resposta é a fonte de verdade — não duplicar o número aqui.
const PASSWORD_FIELDS = new Set(["nova_senha", "senha", "senha_atual"]);

function translatePydanticItem(item) {
  const loc = Array.isArray(item.loc) ? item.loc.filter((p) => p !== "body").join(".") : "";
  const type = item.type || "";
  const ctx = item.ctx || {};

  if (PASSWORD_FIELDS.has(loc)) {
    if (type === "string_too_short") return `A senha deve ter no mínimo ${ctx.min_length} caracteres.`;
    if (type === "string_too_long") return `A senha pode ter no máximo ${ctx.max_length} caracteres.`;
  }

  if (type === "missing") return loc ? `Campo obrigatório: ${loc}.` : "Campo obrigatório não preenchido.";
  if (loc === "email" && (type.includes("email") || /email/i.test(item.msg || ""))) return "E-mail inválido.";

  const msg = item.msg || item.message || "inválido";
  return loc ? `${loc}: ${msg}` : msg;
}

function extractDetailAndCode(data, status) {
  let message = HTTP_STATUS_MESSAGES[status] || `Erro HTTP ${status}`;
  let errorCode = null;

  if (!data) return { message, errorCode };

  const detail = data.detail;

  if (detail && typeof detail === "object" && !Array.isArray(detail) && typeof detail.detail === "string") {
    // Formato novo
    message = detail.detail;
    errorCode = detail.error_code || null;
  } else if (Array.isArray(detail)) {
    // Pydantic v2
    message = detail.map(translatePydanticItem).join(" | ");
  } else if (typeof detail === "string" && detail.trim()) {
    message = detail;
  } else if (typeof data.message === "string") {
    message = data.message;
  }

  return { message, errorCode };
}

/**
 * Cria um Error padronizado com `status` e `errorCode` anexados.
 * Compatível com o consumo antigo: `error.message` continua exibível.
 */
function makeApiError(message, status, errorCode) {
  const err = new Error(message);
  err.status = status;
  err.errorCode = errorCode;
  return err;
}

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
        credentials: "omit",
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
  const merged = { ...init, credentials: "omit", headers: { ...headers, ...(init.headers || {}) } };
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

async function safeJson(response) {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

export async function apiGet(endpoint) {
  const response = await authFetch(endpoint, { method: "GET" });
  const data = await safeJson(response);
  if (!response.ok) {
    const { message, errorCode } = extractDetailAndCode(data, response.status);
    throw makeApiError(message, response.status, errorCode);
  }
  return data;
}

export async function apiPost(endpoint, body) {
  const response = await authFetch(
    endpoint,
    { method: "POST", body: JSON.stringify(body) },
    "application/json"
  );
  const data = await safeJson(response);
  if (!response.ok) {
    const { message, errorCode } = extractDetailAndCode(data, response.status);
    throw makeApiError(message, response.status, errorCode);
  }
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
    credentials: "omit",
  });

  if (response.status === 401) {
    const newToken = await tryRefreshToken();
    if (newToken) {
      headers["Authorization"] = `Bearer ${newToken}`;
      response = await fetch(`${API_URL}${endpoint}`, {
        method: "POST",
        headers,
        body: formData,
        credentials: "omit",
      });
    } else {
      await clearSession();
    }
  }

  const data = await safeJson(response);
  if (!response.ok) {
    const { message, errorCode } = extractDetailAndCode(data, response.status);
    throw makeApiError(message, response.status, errorCode);
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
    credentials: "omit",
  });

  const data = await safeJson(response);
  if (!response.ok) {
    const { message, errorCode } = extractDetailAndCode(data, response.status);
    throw makeApiError(message, response.status, errorCode);
  }
  return data;
}

// Re-exporta utilitário para que telas possam transformar erros em mensagens amigáveis.
export { friendlyErrorMessage };

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
