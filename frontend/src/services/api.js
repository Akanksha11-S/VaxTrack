// Thin wrapper around fetch for the VaxTrack API.
const BASE = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "");
const TOKEN_KEY = "vaxtrack.token";

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

let onUnauthorized = () => {};
export const setUnauthorizedHandler = (fn) => { onUnauthorized = fn; };

export class ApiError extends Error {
  constructor(message, status, data) {
    super(message);
    this.status = status;
    this.data = data;
    this.code = data?.detail?.code || null;
    this.fieldErrors = Array.isArray(data?.errors)
      ? Object.fromEntries(data.errors.map((e) => [e.field, e.message]))
      : {};
  }
}

function messageFrom(data, status) {
  const d = data?.detail;
  if (typeof d === "string") return d;
  if (d && typeof d === "object" && d.message) return d.message;
  if (status === 0) return "Can't reach the VaxTrack server. Check that the backend is running.";
  if (status >= 500) return "Something went wrong on the server. Please try again.";
  return "That didn't work. Please try again.";
}

async function request(path, { method = "GET", body, form, signal, raw = false, auth = true } = {}) {
  const headers = {};
  const token = tokenStore.get();
  if (auth && token) headers.Authorization = `Bearer ${token}`;
  let payload;
  if (form) payload = form;
  else if (body !== undefined) { headers["Content-Type"] = "application/json"; payload = JSON.stringify(body); }

  let res;
  try {
    res = await fetch(`${BASE}${path}`, { method, headers, body: payload, signal });
  } catch (err) {
    if (err.name === "AbortError") throw err;
    throw new ApiError(messageFrom(null, 0), 0, null);
  }
  if (!res.ok) {
    let data = null;
    try { data = await res.json(); } catch { /* not JSON */ }
    if (res.status === 401 && auth && token) onUnauthorized();
    throw new ApiError(messageFrom(data, res.status), res.status, data);
  }
  if (res.status === 204) return null;
  if (raw) return res;
  return res.json();
}

export const api = {
  register: (body) => request("/auth/register", { method: "POST", body, auth: false }),
  login: (body) => request("/auth/login", { method: "POST", body, auth: false }),
  me: () => request("/auth/me"),
  getProfile: () => request("/profile"),
  updateProfile: (body) => request("/profile", { method: "PUT", body }),

  uploadDocument: (file, signal) => { const form = new FormData(); form.append("file", file); return request("/documents/upload", { method: "POST", form, signal }); },
  extractDocument: (id, signal) => request(`/documents/${id}/extract`, { method: "POST", signal }),
  listDocuments: () => request("/documents"),
  deleteDocument: (id) => request(`/documents/${id}`, { method: "DELETE" }),

  listRecords: () => request("/vaccinations"),
  timeline: () => request("/vaccinations/timeline"),
  createRecord: (body) => request("/vaccinations", { method: "POST", body }),
  createBulk: (body) => request("/vaccinations/bulk", { method: "POST", body }),
  updateRecord: (id, body) => request(`/vaccinations/${id}`, { method: "PUT", body }),
  deleteRecord: (id) => request(`/vaccinations/${id}`, { method: "DELETE" }),

  dashboard: () => request("/dashboard/summary"),
  scheduleStatus: () => request("/schedule/status"),
  scheduleOptions: () => request("/schedule/options"),

  vaccines: (params = {}) => request(`/vaccines?${new URLSearchParams(params)}`),
  assistantStatus: () => request("/assistant/status"),
  explain: (body) => request("/assistant/explain", { method: "POST", body }),

  reminders: () => request("/reminders"),
  updateReminder: (id, status) => request(`/reminders/${id}`, { method: "PUT", body: { status } }),
  recalcReminders: () => request("/reminders/recalculate", { method: "POST" }),

  async downloadReport() {
    const res = await request("/reports/vaccination-pdf", { raw: true });
    const blob = await res.blob();
    const match = /filename="?([^"]+)"?/.exec(res.headers.get("Content-Disposition") || "");
    return { blob, filename: match ? match[1] : "vaxtrack-report.pdf" };
  },
};
