import { useId } from "react";

export function FieldWrap({ label, hint, error, id, children, optional }) {
  return (
    <div>
      <label htmlFor={id} className="mb-1.5 block text-sm font-medium">
        {label}{optional && <span className="ml-1.5 font-normal text-ink-muted">optional</span>}
      </label>
      {children}
      {hint && !error && <p id={`${id}-hint`} className="mt-1.5 text-xs text-ink-muted">{hint}</p>}
      {error && <p id={`${id}-err`} className="mt-1.5 text-xs font-medium text-rose-700" role="alert">{error}</p>}
    </div>
  );
}

export function TextField({ label, hint, error, optional, className = "", ...rest }) {
  const id = useId();
  return (
    <FieldWrap label={label} hint={hint} error={error} id={id} optional={optional}>
      <input id={id} className={`field ${className}`} aria-invalid={error ? "true" : undefined}
        aria-describedby={error ? `${id}-err` : hint ? `${id}-hint` : undefined} {...rest} />
    </FieldWrap>
  );
}

export function SelectField({ label, hint, error, optional, children, ...rest }) {
  const id = useId();
  return (
    <FieldWrap label={label} hint={hint} error={error} id={id} optional={optional}>
      <select id={id} className="field" aria-invalid={error ? "true" : undefined} {...rest}>{children}</select>
    </FieldWrap>
  );
}

export function TextArea({ label, hint, error, optional, ...rest }) {
  const id = useId();
  return (
    <FieldWrap label={label} hint={hint} error={error} id={id} optional={optional}>
      <textarea id={id} rows={3} className="field resize-y" aria-invalid={error ? "true" : undefined} {...rest} />
    </FieldWrap>
  );
}

export function Toggle({ checked, onChange, label, description }) {
  const id = useId();
  return (
    <div className="flex items-start justify-between gap-4">
      <div>
        <label htmlFor={id} className="text-sm font-medium">{label}</label>
        {description && <p className="mt-0.5 text-sm text-ink-muted">{description}</p>}
      </div>
      <button id={id} type="button" role="switch" aria-checked={checked} onClick={() => onChange(!checked)}
        className={`relative mt-0.5 inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors ${checked ? "bg-teal-600" : "bg-line-strong"}`}>
        <span className={`inline-block h-5 w-5 rounded-full bg-white shadow transition-transform ${checked ? "translate-x-[22px]" : "translate-x-0.5"}`} />
      </button>
    </div>
  );
}
