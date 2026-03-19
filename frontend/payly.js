const PAYLY_API_BASE_URL = "http://127.0.0.1:8001";

function getToken() {
  return localStorage.getItem("payly_token");
}

function setToken(token) {
  localStorage.setItem("payly_token", token);
}

function clearToken() {
  localStorage.removeItem("payly_token");
}

async function apiFetch(path, { method = "GET", body, auth = false } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (auth) {
    const token = getToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${PAYLY_API_BASE_URL}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  const contentType = res.headers.get("content-type") || "";
  const isJson = contentType.includes("application/json");
  const data = isJson ? await res.json().catch(() => null) : null;

  if (!res.ok) {
    const detail =
      (data && (data.detail || data.message)) ||
      `HTTP ${res.status} ${res.statusText}`;
    const err = new Error(detail);
    err.status = res.status;
    err.data = data;
    throw err;
  }

  return data;
}

function setFormError(el, message) {
  if (!el) return;
  el.textContent = message || "";
  el.classList.toggle("d-none", !message);
}

