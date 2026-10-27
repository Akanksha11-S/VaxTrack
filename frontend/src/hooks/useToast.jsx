import { createContext, useCallback, useContext, useMemo, useRef, useState } from "react";
import { AlertCircle, CheckCircle2, X } from "lucide-react";

const ToastContext = createContext(null);

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const nextId = useRef(1);

  const dismiss = useCallback((id) => setToasts((t) => t.filter((x) => x.id !== id)), []);
  const push = useCallback((kind, message) => {
    const id = nextId.current++;
    setToasts((t) => [...t, { id, kind, message }]);
    setTimeout(() => dismiss(id), kind === "error" ? 7000 : 4000);
  }, [dismiss]);

  const api = useMemo(() => ({ success: (m) => push("success", m), error: (m) => push("error", m) }), [push]);

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div className="pointer-events-none fixed inset-x-0 bottom-20 z-[60] flex flex-col items-center gap-2 px-4 lg:bottom-6 lg:items-end lg:px-6" role="status" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} className="pointer-events-auto flex w-full max-w-sm items-start gap-3 rounded-panel border border-line bg-white p-3.5 shadow-lift">
            {t.kind === "error"
              ? <AlertCircle className="mt-0.5 h-5 w-5 shrink-0 text-rose-700" aria-hidden />
              : <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-sage-700" aria-hidden />}
            <p className="flex-1 text-sm leading-snug">{t.message}</p>
            <button onClick={() => dismiss(t.id)} className="rounded p-0.5 text-ink-muted hover:text-ink" aria-label="Dismiss message"><X className="h-4 w-4" /></button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export const useToast = () => useContext(ToastContext);
