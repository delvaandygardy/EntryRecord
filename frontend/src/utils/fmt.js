const TZ = "America/Port-au-Prince"; // GMT-5

export function fmtDate(ts) {
  if (!ts) return "—";
  return new Date(ts).toLocaleString("fr", {
    timeZone: TZ,
    year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit",
  });
}

export function fmtTime(ts) {
  if (!ts) return "—";
  return new Date(ts).toLocaleTimeString("fr", { timeZone: TZ, hour: "2-digit", minute: "2-digit" });
}

export function nowTZ() {
  return new Date().toLocaleString("fr", {
    timeZone: TZ,
    hour: "2-digit", minute: "2-digit", second: "2-digit",
  });
}

export function nowDateTZ() {
  return new Date().toLocaleDateString("fr", { timeZone: TZ });
}
