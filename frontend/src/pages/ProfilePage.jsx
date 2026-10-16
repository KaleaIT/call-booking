import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";
import { fmtRange } from "../lib.jsx";

export default function ProfilePage() {
  const { ownerId } = useParams();
  const { user: me } = useAuth();
  const isOwn = me && String(me.id) === String(ownerId);

  const [host, setHost] = useState(null);
  const [slots, setSlots] = useState([]);
  const [error, setError] = useState("");
  const [okMsg, setOkMsg] = useState("");
  const [loading, setLoading] = useState(true);

  async function load() {
    setError("");
    try {
      const [h, s] = await Promise.all([
        api.getUser(ownerId),
        api.ownerSlots(ownerId, true),
      ]);
      setHost(h);
      setSlots(s);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [ownerId]);

  async function book(slotId) {
    setError("");
    setOkMsg("");
    try {
      await api.bookSlot(slotId);
      setOkMsg("Готово! Слот забронирован.");
      load();
    } catch (err) {
      setError(err.message);
    }
  }

  if (loading) return <div className="page"><div className="card">Загрузка…</div></div>;

  if (!host) {
    return (
      <div className="page">
        <div className="card">
          <h2>Хозяин не найден</h2>
          <p className="muted">Похоже, такой страницы записи нет.</p>
          <Link className="btn" to="/" style={{ marginTop: 12, display: "inline-block" }}>На главную</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="page stack">
      <section className="card">
        <div className="eyebrow">Страница записи</div>
        <h1 style={{ fontSize: 42, margin: "10px 0 6px" }}>{host.full_name || "Хозяин"}</h1>
        <p className="muted">{host.email}</p>
        <p style={{ marginTop: 14 }}>Выберите удобный слот — он сразу станет вашим.</p>
      </section>

      {okMsg && <p className="notice ok">{okMsg}</p>}
      {error && <p className="notice err">{error}</p>}

      {!me && (
        <p className="notice err">
          Чтобы забронировать слот, <Link to="/" style={{ textDecoration: "underline" }}>войдите в аккаунт</Link>.
        </p>
      )}
      {isOwn && <p className="notice ok">Это ваша страница. Гости будут видеть её именно так.</p>}

      <section className="card">
        <div className="card-title">
          <h2>Свободные слоты</h2>
          <button className="btn sm ghost" onClick={load}>Обновить</button>
        </div>
        {slots.length === 0 ? (
          <div className="empty">Свободных слотов сейчас нет.</div>
        ) : (
          slots.map((s) => {
            const { day, time } = fmtRange(s.start_time, s.end_time);
            return (
              <div className="slot" key={s.id}>
                <div className="when">
                  <b>{day}</b>
                  <span>{time}</span>
                </div>
                <button
                  className="btn primary sm"
                  disabled={!me || isOwn}
                  onClick={() => book(s.id)}
                  title={!me ? "Войдите, чтобы забронировать" : isOwn ? "Нельзя забронировать свой слот" : ""}
                >
                  Забронировать
                </button>
              </div>
            );
          })
        )}
      </section>
    </div>
  );
}
