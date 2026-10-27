export default function PageHeader({ title, description, actions }) {
  return (
    <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div className="min-w-0">
        <h1 className="page-title">{title}</h1>
        {description && <p className="mt-1.5 max-w-2xl text-[0.95rem] leading-relaxed text-ink-muted">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </header>
  );
}
