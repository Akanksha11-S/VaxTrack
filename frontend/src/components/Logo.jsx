export function LogoMark({ className = "h-8 w-8" }) {
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden="true">
      <rect width="32" height="32" rx="8" fill="#0E7C73" />
      <path d="M9 16.5l4.5 4.5L23 11" fill="none" stroke="#fff" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export default function Logo({ className = "" }) {
  return (
    <span className={`inline-flex items-center gap-2.5 ${className}`}>
      <LogoMark />
      <span className="font-serif text-xl font-semibold tracking-tight text-ink">VaxTrack</span>
    </span>
  );
}
