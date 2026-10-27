const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

// Parse "YYYY-MM-DD" as a local date (new Date("2024-03-05") would be UTC and can shift a day).
export function parseISO(iso) {
  if (!iso) return null;
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  return new Date(y, m - 1, d);
}

export function formatDate(iso, fallback = "Date not recorded") {
  const d = parseISO(iso);
  return d ? `${d.getDate()} ${MONTHS[d.getMonth()]} ${d.getFullYear()}` : fallback;
}

export function formatMonthYear(iso) {
  const d = parseISO(iso);
  return d ? `${MONTHS[d.getMonth()]} ${d.getFullYear()}` : "";
}

export function todayISO() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export function daysFromNow(iso) {
  const d = parseISO(iso);
  if (!d) return null;
  const t = new Date(); t.setHours(0, 0, 0, 0);
  return Math.round((d - t) / 86400000);
}

export function relativeDays(iso) {
  const n = daysFromNow(iso);
  if (n === null) return "";
  if (n === 0) return "today";
  const abs = Math.abs(n);
  let span;
  if (abs < 14) span = `${abs} day${abs === 1 ? "" : "s"}`;
  else if (abs < 70) span = `${Math.round(abs / 7)} weeks`;
  else if (abs < 700) span = `${Math.round(abs / 30.4)} months`;
  else span = `${(abs / 365).toFixed(1).replace(".0", "")} years`;
  return n > 0 ? `in ${span}` : `${span} ago`;
}

export function formatAge(age) {
  if (!age) return "";
  if (age.years >= 2) return `${age.years} years`;
  if (age.years === 1 || age.months >= 1) return `${age.years * 12 + age.months} months`;
  return `${age.days} day${age.days === 1 ? "" : "s"}`;
}

export function doseText(n) {
  return n === null || n === undefined ? "Dose not recorded" : n === 0 ? "Dose 0 (birth)" : `Dose ${n}`;
}

export function greeting() {
  const h = new Date().getHours();
  return h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening";
}

// Schedule status -> tone. Green = recorded, amber = upcoming / needs review, red = possibly overdue.
export const STATUS = {
  recorded: { label: "Recorded", tone: "green" },
  upcoming: { label: "Upcoming", tone: "amber" },
  potentially_due: { label: "Potentially due", tone: "amber" },
  possibly_missed: { label: "Possibly missed", tone: "red" },
  needs_verification: { label: "Needs verification", tone: "amber" },
  not_enough_information: { label: "Not enough information", tone: "neutral" },
};
export const STATUS_ORDER = Object.keys(STATUS);

export const TONE_CLASS = {
  green: { badge: "bg-sage-50 text-sage-700 ring-sage-100", dot: "bg-sage-500", solid: "bg-sage-500" },
  amber: { badge: "bg-amber-50 text-amber-700 ring-amber-100", dot: "bg-amber-500", solid: "bg-amber-500" },
  red: { badge: "bg-rose-50 text-rose-700 ring-rose-100", dot: "bg-rose-500", solid: "bg-rose-500" },
  blue: { badge: "bg-azure-50 text-azure-700 ring-azure-100", dot: "bg-azure-600", solid: "bg-azure-600" },
  neutral: { badge: "bg-paper text-ink-soft ring-line-strong", dot: "bg-ink-muted", solid: "bg-line-strong" },
};
