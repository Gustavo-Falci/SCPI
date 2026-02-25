const API_URL = "http://192.168.15.149:8000"; 
// exemplo: http://192.168.0.15:8000
// NÃO use localhost no celular!

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
