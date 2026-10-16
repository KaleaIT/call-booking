// API client. Requests go through the nginx gateway, which routes
// /auth /booking /analytics to the backend services. Empty base => same origin.
const BASE = import.meta.env.VITE_API_BASE ?? "";

function getToken() {
  return localStorage.getItem("token");
}

async function request(path, { method = "GET", body, auth = true } = {}) {
  const headers = {};
  if (body) headers["Content-Type"] = "application/json";
  if (auth && getToken()) headers["Authorization"] = `Bearer ${getToken()}`;

  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail || detail;
    } catch (_) {}
    const err = new Error(detail);
    err.status = res.status;
    throw err;
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  // ── auth ──────────────────────────────────────────────────
  register: (email, password, full_name) =>
    request("/auth/register", { method: "POST", auth: false, body: { email, password, full_name } }),

  async login(email, password) {
    const { access_token } = await request("/auth/login", {
      method: "POST",
      auth: false,
      body: { email, password },
    });
    localStorage.setItem("token", access_token);
    const me = await request("/auth/me");
    localStorage.setItem("user", JSON.stringify(me));
    return me;
  },

  logout() {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
  },

  currentUser() {
    const u = localStorage.getItem("user");
    return u ? JSON.parse(u) : null;
  },
  isAuthed: () => !!getToken(),

  getUser: (id) => request(`/auth/users/${id}`, { auth: false }),

  // ── notifications (WebSocket) ─────────────────────────────
  // Token goes in the query string because browsers can't set headers on a
  // WebSocket handshake. Routed by the gateway to notification-ws.
  notificationsSocketUrl() {
    const token = getToken();
    if (!token) return null;
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    return `${proto}//${window.location.host}${BASE}/notifications/ws?token=${token}`;
  },

  // ── slots / bookings ──────────────────────────────────────
  ownerSlots: (ownerId, availableOnly = true) =>
    request(`/booking/slots?owner_id=${ownerId}&available_only=${availableOnly}`, { auth: false }),

  mySlots() {
    const me = this.currentUser();
    return request(`/booking/slots?owner_id=${me.id}&available_only=false`);
  },

  createSlot: (start_time, end_time) =>
    request("/booking/slots", { method: "POST", body: { start_time, end_time } }),

  bookSlot: (slotId) => request(`/booking/slots/${slotId}/book`, { method: "POST" }),
  cancelBooking: (bookingId) => request(`/booking/bookings/${bookingId}/cancel`, { method: "POST" }),
  myBookings: () => request("/booking/bookings/mine"),

  // Set meeting description / link on a booked slot (host or guest).
  updateSlot: (slotId, { description, meeting_link }) =>
    request(`/booking/slots/${slotId}`, {
      method: "PATCH",
      body: { description, meeting_link },
    }),

  // ── google calendar ───────────────────────────────────────
  googleStatus: () => request("/calendar/google/status"),
  googleAuthorize: () => request("/calendar/google/authorize"),
  googleDisconnect: () => request("/calendar/google/disconnect", { method: "POST" }),

  // ── analytics ─────────────────────────────────────────────
  stats: () => request("/analytics/stats", { auth: false }),
};
