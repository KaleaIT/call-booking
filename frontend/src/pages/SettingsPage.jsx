import React, { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";

export default function SettingsPage() {
  const { user: me } = useAuth();
  const [status, setStatus] = useState(null); // { connected, google_email }
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    setError("");
    try {
      setStatus(await api.googleStatus());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (me) refresh();
  }, [me, refresh]);

  // The OAuth popup posts a message back here once Google redirects to the
  // callback; we just re-read the connection status.
  useEffect(() => {
    function onMessage(e) {
      if (e.data && e.data.source === "google-oauth") {
        setBusy(false);
        refresh();
      }
    }
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, [refresh]);

  async function connect() {
    setError("");
    setBusy(true);
    try {
      const { url } = await api.googleAuthorize();
      const w = 520;
      const h = 640;
      const left = window.screenX + (window.outerWidth - w) / 2;
      const top = window.screenY + (window.outerHeight - h) / 2;
      const popup = window.open(
        url,
        "google-oauth",
        `width=${w},height=${h},left=${left},top=${top}`
      );
      if (!popup) {
        // Popup blocked — fall back to a full-page redirect.
        window.location.assign(url);
      }
    } catch (err) {
      setBusy(false);
      setError(err.message);
    }
  }

  async function disconnect() {
    setError("");
    setBusy(true);
    try {
      await api.googleDisconnect();
      await refresh();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  if (!me) {
    return (
      <div className="page">
        <div className="card">
          <h2>Нужен вход</h2>
          <p className="muted">Войдите в аккаунт, чтобы управлять настройками.</p>
          <Link className="btn" to="/" style={{ marginTop: 12, display: "inline-block" }}>
            На главную
          </Link>
        </div>
      </div>
    );
  }

  const connected = status?.connected;

  return (
    <div className="page stack">
      <section className="card">
        <div className="eyebrow">Настройки</div>
        <h1 style={{ fontSize: 36, margin: "10px 0 6px" }}>Интеграции</h1>
        <p className="muted">
          Подключите Google Calendar — и каждая бронь будет автоматически попадать
          в&nbsp;ваш календарь, а&nbsp;второй участник добавится как гость.
        </p>
      </section>

      {error && <p className="notice err">{error}</p>}

      <section className="card">
        <div className="card-title">
          <h2>Google Calendar</h2>
          {!loading && (
            <span className={`badge ${connected ? "booked" : "available"}`}>
              {connected ? "подключено" : "не подключено"}
            </span>
          )}
        </div>

        {loading ? (
          <div className="empty">Загрузка…</div>
        ) : connected ? (
          <>
            <p style={{ margin: "6px 0 16px" }}>
              Подключён аккаунт <b>{status.google_email || "Google"}</b>. Новые встречи
              будут создаваться в этом календаре.
            </p>
            <button className="btn" disabled={busy} onClick={disconnect}>
              {busy ? "…" : "Отключить"}
            </button>
          </>
        ) : (
          <>
            <p style={{ margin: "6px 0 16px" }}>
              <a
                role="button"
                tabIndex={0}
                onClick={connect}
                onKeyDown={(e) => (e.key === "Enter" ? connect() : null)}
                style={{ cursor: "pointer", textDecoration: "underline", fontWeight: 600 }}
              >
                Подключите Google-аккаунт для интеграции с календарём
              </a>{" "}
              — откроется окно согласия Google.
            </p>
            <button className="btn primary" disabled={busy} onClick={connect}>
              {busy ? "Ожидание подтверждения…" : "Подключить Google Calendar"}
            </button>
          </>
        )}
      </section>
    </div>
  );
}
