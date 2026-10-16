import React, { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";
import { useNotifications } from "../notifications.jsx";
import { fmtRange } from "../lib.jsx";

export default function DashboardPage() {
  const { user: me } = useAuth();
  const [slots, setSlots] = useState([]);
  const [bookings, setBookings] = useState([]);
  const [users, setUsers] = useState({}); // id -> {full_name, email}
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

  const shareUrl = `${window.location.origin}/u/${me.id}`;

  // Resolve counterpart names — booking-service only returns user ids.
  const ensureUsers = useCallback(async (ids) => {
    const unique = [...new Set(ids.filter((id) => id != null))];
    const pairs = await Promise.all(
      unique.map(async (id) => {
        try {
          return [id, await api.getUser(id)];
        } catch (_) {
          return [id, null];
        }
      })
    );
    setUsers((prev) => {
      const next = { ...prev };
      for (const [id, u] of pairs) next[id] = u;
      return next;
    });
  }, []);

  const refresh = useCallback(async () => {
    setError("");
    try {
      const [s, b] = await Promise.all([api.mySlots(), api.myBookings()]);
      setSlots(s);
      setBookings(b);
      ensureUsers([
        ...b.map((x) => x.owner_id),
        ...s.filter((x) => x.status !== "available").map((x) => x.booked_by_user_id),
      ]);
    } catch (err) {
      setError(err.message);
    }
  }, [ensureUsers]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  function userName(id) {
    const u = users[id];
    return (u && (u.full_name || u.email)) || `пользователь #${id}`;
  }

  async function addSlot(e) {
    e.preventDefault();
    setError("");
    try {
      await api.createSlot(new Date(start).toISOString(), new Date(end).toISOString());
      setStart("");
      setEnd("");
      refresh();
    } catch (err) {
      setError(err.message);
    }
  }

  async function cancel(id) {
    setError("");
    try {
      await api.cancelBooking(id);
      refresh();
    } catch (err) {
      setError(err.message);
    }
  }

  function copy() {
    navigator.clipboard?.writeText(shareUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  const upcoming = slots.filter((s) => s.status === "available");
  const taken = slots.filter((s) => s.status !== "available");

  return (
    <div className="page stack">
      {/* header + share */}
      <section className="card">
        <div className="eyebrow">Личный кабинет</div>
        <h1 style={{ fontSize: 40, margin: "10px 0 6px" }}>
          Здравствуйте, {me.full_name || "гость"}.
        </h1>
        <p className="muted" style={{ marginBottom: 22 }}>
          Опубликуйте свободные слоты ниже и&nbsp;поделитесь ссылкой — гости выберут время сами.
        </p>
        <div className="eyebrow" style={{ marginBottom: 8 }}>Ваша публичная ссылка</div>
        <div className="copy-row">
          <code>{shareUrl}</code>
          <button className="btn sm" onClick={copy}>{copied ? "Скопировано" : "Копировать"}</button>
          <Link className="btn sm ghost" to={`/u/${me.id}`}>Открыть</Link>
        </div>
      </section>

      {error && <p className="notice err">{error}</p>}

      <NotificationsPanel />

      <div className="grid-2">
        {/* create availability */}
        <section className="card">
          <div className="card-title"><h2>Новый слот</h2></div>
          <form onSubmit={addSlot}>
            <div className="field">
              <label>Начало</label>
              <input className="input" type="datetime-local" required value={start} onChange={(e) => setStart(e.target.value)} />
            </div>
            <div className="field">
              <label>Окончание</label>
              <input className="input" type="datetime-local" required value={end} onChange={(e) => setEnd(e.target.value)} />
            </div>
            <button className="btn primary block" type="submit">Опубликовать слот</button>
          </form>
        </section>

        {/* my bookings (as guest) */}
        <section className="card">
          <div className="card-title">
            <h2>Мои брони</h2>
            <button className="btn sm ghost" onClick={refresh}>Обновить</button>
          </div>
          {bookings.length === 0 ? (
            <div className="empty">Вы пока ничего не бронировали.</div>
          ) : (
            bookings.map((b) => {
              const { day, time } = fmtRange(b.start_time, b.end_time);
              return (
                <div className="slot col" key={b.id}>
                  <div className="slot-head">
                    <div className="when">
                      <b>Созвон с {userName(b.owner_id)}</b>
                      <span>{[day, time].filter(Boolean).join(" · ")}</span>
                    </div>
                    <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                      <span className={`badge ${b.status}`}>{b.status === "active" ? "активна" : "отменена"}</span>
                      {b.status === "active" && (
                        <button className="btn sm" onClick={() => cancel(b.id)}>Отменить</button>
                      )}
                    </div>
                  </div>
                  {b.status === "active" && (
                    <MeetingDetails
                      slotId={b.slot_id}
                      description={b.description}
                      meetingLink={b.meeting_link}
                      onSaved={refresh}
                    />
                  )}
                </div>
              );
            })
          )}
        </section>
      </div>

      {/* my availability */}
      <section className="card">
        <div className="card-title">
          <h2>Моя доступность</h2>
          <span className="muted">{upcoming.length} свободно · {taken.length} занято</span>
        </div>
        {slots.length === 0 ? (
          <div className="empty">Слотов пока нет. Опубликуйте первый выше.</div>
        ) : (
          <>
            {upcoming.map((s) => <SlotRow key={s.id} slot={s} userName={userName} onSaved={refresh} />)}
            {taken.map((s) => <SlotRow key={s.id} slot={s} userName={userName} onSaved={refresh} />)}
          </>
        )}
      </section>
    </div>
  );
}

function NotificationsPanel() {
  const { items } = useNotifications();
  return (
    <section className="card">
      <div className="card-title">
        <h2>Уведомления</h2>
        <span className="muted">в реальном времени</span>
      </div>
      {items.length === 0 ? (
        <div className="empty">Здесь появятся уведомления о бронированиях и отменах.</div>
      ) : (
        items.map((n) => {
          const meta = n.start_time ? fmtRange(n.start_time, n.end_time) : null;
          const cls = n.kind === "booking.cancelled" ? "cancelled" : "active";
          return (
            <div className="slot" key={n.id}>
              <div className="when">
                <b>{n.text}</b>
                {meta && <span>{meta.day} · {meta.time}</span>}
              </div>
              <span className={`badge ${cls}`}>
                {n.kind === "booking.cancelled" ? "отмена" : "бронь"}
              </span>
            </div>
          );
        })
      )}
    </section>
  );
}

function SlotRow({ slot, userName, onSaved }) {
  const { day, time } = fmtRange(slot.start_time, slot.end_time);
  const isBooked = slot.status !== "available";
  const label = isBooked ? "забронирован" : "свободен";

  if (!isBooked) {
    return (
      <div className="slot">
        <div className="when">
          <b>{day}</b>
          <span>{time}</span>
        </div>
        <span className={`badge ${slot.status}`}>{label}</span>
      </div>
    );
  }

  return (
    <div className="slot col">
      <div className="slot-head">
        <div className="when">
          <b>{day}</b>
          <span>
            {time}
            {slot.booked_by_user_id != null && ` · забронировал ${userName(slot.booked_by_user_id)}`}
          </span>
        </div>
        <span className={`badge ${slot.status}`}>{label}</span>
      </div>
      <MeetingDetails
        slotId={slot.id}
        description={slot.description}
        meetingLink={slot.meeting_link}
        onSaved={onSaved}
      />
    </div>
  );
}

// Shows the meeting description + link for a booked slot, with an inline editor.
// Either participant may edit (the backend enforces the permission).
function MeetingDetails({ slotId, description, meetingLink, onSaved }) {
  const [editing, setEditing] = useState(false);
  const [desc, setDesc] = useState(description || "");
  const [link, setLink] = useState(meetingLink || "");
  const [err, setErr] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setDesc(description || "");
    setLink(meetingLink || "");
  }, [description, meetingLink]);

  async function save() {
    setSaving(true);
    setErr("");
    try {
      await api.updateSlot(slotId, { description: desc, meeting_link: link });
      setEditing(false);
      onSaved && onSaved();
    } catch (e) {
      setErr(e.message);
    } finally {
      setSaving(false);
    }
  }

  if (!editing) {
    const hasDetails = description || meetingLink;
    return (
      <div className="meeting">
        {description && <div className="desc">{description}</div>}
        {meetingLink && (
          <div className="row">
            <a className="link" href={meetingLink} target="_blank" rel="noreferrer">{meetingLink}</a>
          </div>
        )}
        <div className="row">
          <button className="btn sm ghost" onClick={() => setEditing(true)}>
            {hasDetails ? "Изменить детали" : "Добавить описание и ссылку"}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="meeting">
      <div className="field">
        <label>Описание созвона</label>
        <input className="input" value={desc} onChange={(e) => setDesc(e.target.value)} placeholder="Например: обсуждение проекта" />
      </div>
      <div className="field">
        <label>Ссылка на место встречи</label>
        <input className="input" value={link} onChange={(e) => setLink(e.target.value)} placeholder="https://meet.google.com/…" />
      </div>
      {err && <p className="notice err">{err}</p>}
      <div className="row">
        <button className="btn primary sm" disabled={saving} onClick={save}>{saving ? "Сохранение…" : "Сохранить"}</button>
        <button className="btn sm ghost" disabled={saving} onClick={() => setEditing(false)}>Отмена</button>
      </div>
    </div>
  );
}
