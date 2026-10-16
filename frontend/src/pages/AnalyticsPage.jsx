import React, { useEffect, useState } from "react";
import { api } from "../api.js";

export default function AnalyticsPage() {
  const [stats, setStats] = useState(null);
  const [error, setError] = useState("");

  async function load() {
    setError("");
    try {
      setStats(await api.stats());
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <div className="page stack">
      <section className="card">
        <div className="eyebrow">Сводка платформы</div>
        <h1 style={{ fontSize: 40, margin: "10px 0 4px" }}>Аналитика</h1>
        <p className="muted">Агрегированные показатели бронирований из ClickHouse.</p>
      </section>

      {error && <p className="notice err">{error}</p>}

      {!stats ? (
        <div className="card"><div className="empty">Загрузка показателей…</div></div>
      ) : (
        <>
          <div className="grid-3">
            <Tile n={stats.bookings_created} l="Создано броней" />
            <Tile n={stats.active_bookings} l="Активные" />
            <Tile n={stats.bookings_cancelled} l="Отменено" />
          </div>
          <div className="grid-2">
            <Tile n={stats.unique_users} l="Уникальных пользователей" />
            <section className="card">
              <div className="card-title"><h2>Топ по броням</h2></div>
              {(!stats.top_users || stats.top_users.length === 0) ? (
                <div className="empty">Пока нет данных.</div>
              ) : (
                stats.top_users.map((u, i) => (
                  <div className="slot" key={u.user_id}>
                    <div className="when">
                      <b>#{i + 1} · пользователь {u.user_id}</b>
                      <span>идентификатор {u.user_id}</span>
                    </div>
                    <span className="badge available">{u.bookings} броней</span>
                  </div>
                ))
              )}
            </section>
          </div>
          <button className="btn" onClick={load} style={{ alignSelf: "flex-start" }}>Обновить</button>
        </>
      )}
    </div>
  );
}

function Tile({ n, l }) {
  return (
    <div className="stat">
      <div className="n">{n ?? 0}</div>
      <div className="l">{l}</div>
    </div>
  );
}
