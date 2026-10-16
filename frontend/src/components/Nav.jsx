import React, { useEffect, useRef, useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../auth.jsx";
import { useNotifications } from "../notifications.jsx";
import { fmtRange } from "../lib.jsx";

function NotificationBell() {
  const { items, unread, markAllRead } = useNotifications();
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    function onClickOutside(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  function toggle() {
    setOpen((v) => {
      if (!v) markAllRead();
      return !v;
    });
  }

  return (
    <div className="bell-wrap" ref={ref}>
      <button className="bell" onClick={toggle} title="Уведомления" aria-label="Уведомления">
        🔔
        {unread > 0 && <span className="bell-badge">{unread > 9 ? "9+" : unread}</span>}
      </button>
      {open && (
        <div className="bell-menu">
          <div className="bell-menu-title">Уведомления</div>
          {items.length === 0 ? (
            <div className="bell-empty">Пока пусто</div>
          ) : (
            items.map((n) => {
              const meta = n.start_time ? fmtRange(n.start_time, n.end_time) : null;
              return (
                <div className="bell-item" key={n.id}>
                  <div className="bell-item-text">{n.text}</div>
                  {meta && <div className="bell-item-meta">{meta.day} · {meta.time}</div>}
                </div>
              );
            })
          )}
        </div>
      )}
    </div>
  );
}

export default function Nav() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  function onLogout() {
    logout();
    navigate("/");
  }

  return (
    <nav className="nav">
      <NavLink to="/" className="brand">
        Anti<span>qua</span>
      </NavLink>
      <div className="links">
        {user ? (
          <>
            <NavLink to="/" end>Моя страница</NavLink>
            <NavLink to="/settings">Настройки</NavLink>
            <NavLink to="/stats">Аналитика</NavLink>
            <NotificationBell />
            <span className="chip" title={user.email}>{user.full_name || user.email}</span>
            <button className="btn sm ghost" onClick={onLogout}>Выйти</button>
          </>
        ) : (
          <>
            <NavLink to="/stats">Аналитика</NavLink>
            <NavLink to="/" end className="active">Войти</NavLink>
          </>
        )}
      </div>
    </nav>
  );
}
