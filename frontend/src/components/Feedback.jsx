import { AlertCircle, Info, Loader2 } from "lucide-react";
import Button from "./Button.jsx";

export function Spinner({ label = "Loading", className = "" }) {
  return (
    <div className={`flex items-center justify-center gap-2 py-12 text-sm text-ink-muted ${className}`} role="status">
      <Loader2 className="h-5 w-5 animate-spin text-teal-600" aria-hidden />
      <span>{label}</span>
    </div>
  );
}

export function EmptyState({ icon: Icon, title, children, action }) {
  return (
    <div className="flex flex-col items-start gap-1 px-5 py-9 sm:items-center sm:text-center">
      {Icon && <Icon className="mb-2 h-7 w-7 text-teal-600" aria-hidden />}
      <p className="font-medium">{title}</p>
      {children && <p className="max-w-md text-sm text-ink-muted">{children}</p>}
      {action && <div className="mt-3">{action}</div>}
    </div>
  );
}

export function ErrorNotice({ error, onRetry, className = "" }) {
  if (!error) return null;
  return (
    <div className={`flex items-start gap-3 rounded-panel border border-rose-100 bg-rose-50 p-4 text-sm text-rose-700 ${className}`} role="alert">
      <AlertCircle className="mt-0.5 h-5 w-5 shrink-0" aria-hidden />
      <div className="flex-1">
        <p>{error.message || String(error)}</p>
        {onRetry && <Button variant="quiet" onClick={onRetry} className="mt-1 !text-rose-700">Try again</Button>}
      </div>
    </div>
  );
}

export function Notice({ children, tone = "info", className = "" }) {
  const cls = tone === "warn" ? "border-amber-100 bg-amber-50 text-amber-700" : "border-azure-100 bg-azure-50 text-azure-700";
  return (
    <div className={`flex items-start gap-3 rounded-panel border p-4 text-sm leading-relaxed ${cls} ${className}`}>
      <Info className="mt-0.5 h-5 w-5 shrink-0" aria-hidden />
      <div>{children}</div>
    </div>
  );
}

export const SCHEDULE_DISCLAIMER =
  "Vaccination schedules depend on country, age, medical circumstances and official recommendations. VaxTrack uses a simplified reference schedule to organise your records. It is educational and does not replace advice from a healthcare provider.";
