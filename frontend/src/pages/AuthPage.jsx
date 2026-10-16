import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth.jsx";

export default function AuthPage() {
  const navigate = useNavigate();
  const { login, register } = useAuth();
  const [mode, setMode] = useState("login");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      if (mode === "register") {
        await register(email, password, fullName);
      } else {
        await login(email, password);
      }
      navigate("/");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page">
      <div className="grid-2">
        {/* editorial hero */}
        <section className="card" style={{ padding: "44px 42px", overflow: "hidden", position: "relative" }}>
          <div className="eyebrow">Antiqua · запись на встречи</div>
          <h1 style={{ fontSize: 58, lineHeight: 1.02, margin: "18px 0 0", maxWidth: 520 }}>
            Назначайте встречи в&nbsp;античном спокойствии.
          </h1>
          <p className="muted" style={{ maxWidth: 460, marginTop: 18, fontSize: 16 }}>
            Опубликуйте своё свободное время — и&nbsp;дайте другим выбрать удобный
            слот по&nbsp;ссылке. Без переписок и&nbsp;суеты.
          </p>
          <div style={{ display: "flex", gap: 8, marginTop: 26, flexWrap: "wrap" }}>
            <span className="chip">Свободные слоты</span>
            <span className="chip">Бронь по ссылке</span>
            <span className="chip">Спокойный интерфейс</span>
          </div>
          <Laurel />
        </section>

        {/* auth card */}
        <section className="card">
          <div className="tabs" style={{ marginBottom: 22 }}>
            <button className={mode === "login" ? "active" : ""} onClick={() => setMode("login")}>Вход</button>
            <button className={mode === "register" ? "active" : ""} onClick={() => setMode("register")}>Регистрация</button>
          </div>
          <h2 style={{ marginBottom: 18 }}>{mode === "login" ? "С возвращением" : "Создать аккаунт"}</h2>
          <form onSubmit={submit}>
            {mode === "register" && (
              <div className="field">
                <label>Имя</label>
                <input className="input" value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="Кирилл" />
              </div>
            )}
            <div className="field">
              <label>Email</label>
              <input className="input" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" />
            </div>
            <div className="field">
              <label>Пароль</label>
              <input className="input" type="password" required value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" />
            </div>
            <button className="btn primary block" type="submit" disabled={busy} style={{ marginTop: 8 }}>
              {busy ? "Минуту…" : mode === "login" ? "Войти" : "Создать аккаунт"}
            </button>
          </form>
          {error && <p className="notice err" style={{ marginTop: 16 }}>{error}</p>}
        </section>
      </div>
    </div>
  );
}

function Laurel() {
  // subtle classical flourish in the corner
  return (
    <svg width="180" height="180" viewBox="0 0 100 100" aria-hidden="true"
      style={{ position: "absolute", right: -12, bottom: -18, opacity: 0.10 }}>
      <g fill="none" stroke="#2f3a2c" strokeWidth="1.4">
        <path d="M50 92 C 50 60, 50 40, 50 14" />
        {[...Array(7)].map((_, i) => {
          const y = 24 + i * 9;
          return (
            <g key={i}>
              <path d={`M50 ${y} C 36 ${y - 6}, 28 ${y + 2}, 24 ${y + 10}`} />
              <path d={`M50 ${y} C 64 ${y - 6}, 72 ${y + 2}, 76 ${y + 10}`} />
            </g>
          );
        })}
      </g>
    </svg>
  );
}
