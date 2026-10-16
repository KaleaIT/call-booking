import React, { createContext, useContext, useEffect, useRef, useState } from "react";
import { api } from "./api.js";
import { useAuth } from "./auth.jsx";

// Holds the live notification feed for the logged-in user. Opens a single
// WebSocket to the gateway (/api/notifications/ws), replays the short history
// the server sends on connect, then appends live notifications as they arrive.
// Auto-reconnects with backoff and tears down on logout.
const NotificationsCtx = createContext(null);

export function NotificationsProvider({ children }) {
  const { user } = useAuth();
  const [items, setItems] = useState([]);
  const [unread, setUnread] = useState(0);
  const wsRef = useRef(null);
  const retryRef = useRef(null);

  useEffect(() => {
    // No user → make sure any socket is closed and the feed is empty.
    if (!user) {
      setItems([]);
      setUnread(0);
      return;
    }

    let closedByUs = false;
    let attempt = 0;

    function connect() {
      const url = api.notificationsSocketUrl();
      if (!url) return;

      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        attempt = 0;
      };

      ws.onmessage = (ev) => {
        let data;
        try {
          data = JSON.parse(ev.data);
        } catch (_) {
          return;
        }
        if (data.type === "history") {
          // History is the already-seen backlog — show it but don't mark unread.
          setItems(Array.isArray(data.items) ? data.items : []);
        } else if (data && data.id) {
          // Live notification — newest first, bump the unread counter.
          setItems((prev) => [data, ...prev].slice(0, 50));
          setUnread((n) => n + 1);
        }
      };

      ws.onclose = () => {
        if (closedByUs) return;
        // Reconnect with capped exponential backoff.
        const delay = Math.min(1000 * 2 ** attempt, 15000);
        attempt += 1;
        retryRef.current = setTimeout(connect, delay);
      };

      ws.onerror = () => {
        ws.close();
      };
    }

    connect();

    return () => {
      closedByUs = true;
      if (retryRef.current) clearTimeout(retryRef.current);
      if (wsRef.current) wsRef.current.close();
      wsRef.current = null;
    };
  }, [user?.id]);

  function markAllRead() {
    setUnread(0);
  }

  return (
    <NotificationsCtx.Provider value={{ items, unread, markAllRead }}>
      {children}
    </NotificationsCtx.Provider>
  );
}

export function useNotifications() {
  return useContext(NotificationsCtx);
}
