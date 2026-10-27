import { STATUS, TONE_CLASS } from "../utils/format.js";

export function Badge({ tone = "neutral", children, className = "" }) {
  const t = TONE_CLASS[tone];
  return (
    <span className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${t.badge} ${className}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${t.dot}`} aria-hidden />
      {children}
    </span>
  );
}

export function ScheduleStatusBadge({ status }) {
  const s = STATUS[status] || STATUS.not_enough_information;
  return <Badge tone={s.tone}>{s.label}</Badge>;
}

/** Whether a saved record has been checked by the user. */
export function VerificationBadge({ record }) {
  if (record.has_error) return <Badge tone="red">Check this record</Badge>;
  if (record.verification_status === "confirmed") return <Badge tone="green">Confirmed</Badge>;
  return <Badge tone="amber">{record.source_type === "ocr" ? "Read from card, not confirmed" : "Not confirmed"}</Badge>;
}
