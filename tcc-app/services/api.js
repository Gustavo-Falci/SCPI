const API_URL = "http://192.168.5.157:8000";
// exemplo: http://192.168.0.15:8000
// N√ÉO use localhost no celular!

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

export async function apiGet(endpoint) {
  try {
    const headers = await getAuthHeaders();
    const response = await fetch(`${API_URL}${endpoint}`, {
      method: "GET",
      headers,
    });

    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || `Erro HTTP ${response.status}`);
    return data;
  } catch (error) {
    throw error;
  }
}

export async function apiPost(endpoint, body) {
  try {
    const headers = await getAuthHeaders("application/json");
    const response = await fetch(`${API_URL}${endpoint}`, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
    });

    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || `Erro HTTP ${response.status}`);
    return data;
  } catch (error) {
    throw error;
  }
}


export async function apiPostFormData(endpoint, formData) {
    try {
        const token = await storage.getItem("access_token");
        const headers = {
            Accept: "application/json",
        };
        if (token) {
            headers["Authorization"] = `Bearer ${token}`;
        }
        
        // Em React Native (Expo Web), quando enviamos FormData que n„o tem boundary definido no header,
        // N√O podemos passar o Content-Type. O navegador cria isso sozinho com o boundary type.

        const response = await fetch(`${API_URL}${endpoint}`, {
            method: "POST",
            headers,
            body: formData,
        });

        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || `Erro HTTP ${response.status}`);
        return data;
    } catch (error) {
        throw error;
    }
}


export async function loginRequest(email, senha) {
  try {
    const formData = new URLSearchParams();
    formData.append("username", email);
    formData.append("password", senha);

    const response = await fetch(`${API_URL}/auth/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: formData.toString(),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Erro ao fazer login");
    }

    return data;

  } catch (error) {
    throw error;
  }
}
