import { Link } from "react-router-dom";
import Logo from "./Logo.jsx";

/** Two-column frame for sign in / register: the form on the left, a record-card preview on the right. */
export default function AuthShell({ title, subtitle, children, footer }) {
  return (
    <div className="grid min-h-screen lg:grid-cols-[minmax(0,1fr)_minmax(0,30rem)]">
      <div className="flex flex-col px-6 py-8 sm:px-12">
        <Link to="/" aria-label="VaxTrack home"><Logo /></Link>
        <div className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center py-10">
          <h1 className="page-title">{title}</h1>
          <p className="mb-7 mt-2 text-ink-muted">{subtitle}</p>
          {children}
          <p className="mt-6 text-sm text-ink-muted">{footer}</p>
        </div>
      </div>
      <aside className="hidden bg-teal-800 px-12 py-16 text-teal-50 lg:flex lg:flex-col lg:justify-center" aria-hidden="true">
        <p className="font-serif text-2xl leading-snug text-white">Vaccination cards fade, get lost, and are hard to read.</p>
        <p className="mt-4 leading-relaxed text-teal-100">VaxTrack keeps what your card says in one place, so you can check it, correct it and see what may be due next.</p>
        <ul className="mt-8 space-y-3 text-sm text-teal-100">
          <li>You confirm every record. Nothing is counted until you do.</li>
          <li>Estimated dates are labelled as estimates, never as appointments.</li>
          <li>Your documents stay on this server and are removed after 30 days.</li>
        </ul>
      </aside>
    </div>
  );
}
