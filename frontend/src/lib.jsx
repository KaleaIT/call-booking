// Small shared UI helpers.
export function fmtDate(iso) {
  try {
    return new Date(iso).toLocaleString("ru-RU", {
      day: "numeric",
      month: "long",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch (_) {
    return iso;
  }
}

export function fmtRange(start, end) {
  try {
    const s = new Date(start);
    const e = new Date(end);
    const day = s.toLocaleDateString("ru-RU", { day: "numeric", month: "long" });
    const t = (d) => d.toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" });
    return { day, time: `${t(s)} – ${t(e)}` };
  } catch (_) {
    return { day: start, time: "" };
  }
}
