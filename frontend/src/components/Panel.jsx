export function Panel({ children, className = "", as: Tag = "section", ...rest }) {
  return <Tag className={`rounded-panel border border-line bg-white shadow-panel ${className}`} {...rest}>{children}</Tag>;
}

export function PanelHeader({ title, description, action, id }) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3 border-b border-line px-5 py-4">
      <div className="min-w-0">
        <h2 id={id} className="font-serif text-lg font-semibold leading-snug">{title}</h2>
        {description && <p className="mt-0.5 text-sm text-ink-muted">{description}</p>}
      </div>
      {action}
    </div>
  );
}
