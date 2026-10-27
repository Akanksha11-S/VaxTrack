import { useEffect, useRef } from "react";
import { X } from "lucide-react";
import Button from "./Button.jsx";

const FOCUSABLE = 'a[href],button:not([disabled]),textarea,input,select,[tabindex]:not([tabindex="-1"])';

export function Modal({ open, onClose, title, children, footer, wide = false }) {
  const ref = useRef(null);
  const lastFocus = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    lastFocus.current = document.activeElement;
    const node = ref.current;
    const first = node?.querySelector("[data-autofocus]") || node?.querySelector(FOCUSABLE);
    first?.focus();
    document.body.style.overflow = "hidden";
    const onKey = (e) => {
      if (e.key === "Escape") { e.stopPropagation(); onClose(); }
      if (e.key === "Tab" && node) {
        const items = [...node.querySelectorAll(FOCUSABLE)];
        if (!items.length) return;
        const [a, z] = [items[0], items[items.length - 1]];
        if (e.shiftKey && document.activeElement === a) { e.preventDefault(); z.focus(); }
        else if (!e.shiftKey && document.activeElement === z) { e.preventDefault(); a.focus(); }
      }
    };
    document.addEventListener("keydown", onKey);
    return () => { document.removeEventListener("keydown", onKey); document.body.style.overflow = ""; lastFocus.current?.focus?.(); };
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-ink/40 sm:items-center sm:p-6" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div ref={ref} role="dialog" aria-modal="true" aria-label={title}
        className={`flex max-h-[92vh] w-full flex-col rounded-t-2xl bg-white shadow-lift sm:rounded-panel ${wide ? "sm:max-w-2xl" : "sm:max-w-lg"}`}>
        <div className="flex items-center justify-between border-b border-line px-5 py-4">
          <h2 className="font-serif text-lg font-semibold">{title}</h2>
          <button onClick={onClose} className="rounded p-1 text-ink-muted hover:bg-paper hover:text-ink" aria-label="Close"><X className="h-5 w-5" /></button>
        </div>
        <div className="overflow-y-auto px-5 py-5">{children}</div>
        {footer && <div className="flex flex-wrap justify-end gap-2 border-t border-line px-5 py-3.5">{footer}</div>}
      </div>
    </div>
  );
}

export function ConfirmDialog({ open, title, children, confirmLabel = "Delete", onConfirm, onClose, loading, danger = true }) {
  return (
    <Modal open={open} onClose={onClose} title={title}
      footer={<>
        <Button variant="secondary" onClick={onClose}>Cancel</Button>
        <Button variant={danger ? "danger" : "primary"} loading={loading} onClick={onConfirm}>{confirmLabel}</Button>
      </>}>
      <div className="text-sm leading-relaxed text-ink-soft">{children}</div>
    </Modal>
  );
}
