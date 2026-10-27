import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  Bell, BookOpen, CalendarCheck2, FileDown, History, LayoutDashboard, LogOut, Menu, Route, ScanLine, UserRound, X,
} from "lucide-react";
import Logo from "../components/Logo.jsx";
import { useAuth } from "../hooks/useAuth.jsx";

const GROUPS = [
  { title: "Your record", items: [
    { to: "/app", label: "Dashboard", icon: LayoutDashboard, end: true },
    { to: "/app/upload", label: "Upload a card", icon: ScanLine },
    { to: "/app/history", label: "History", icon: History },
    { to: "/app/timeline", label: "Timeline", icon: Route },
  ]},
  { title: "Plan ahead", items: [
    { to: "/app/schedule", label: "Schedule status", icon: CalendarCheck2 },
    { to: "/app/reminders", label: "Reminders", icon: Bell },
    { to: "/app/vaccines", label: "Vaccine information", icon: BookOpen },
  ]},
  { title: "Account", items: [
    { to: "/app/report", label: "PDF report", icon: FileDown },
    { to: "/app/profile", label: "Profile", icon: UserRound },
  ]},
];
const TABS = [
  { to: "/app", label: "Home", icon: LayoutDashboard, end: true },
  { to: "/app/history", label: "History", icon: History },
  { to: "/app/upload", label: "Upload", icon: ScanLine },
  { to: "/app/reminders", label: "Reminders", icon: Bell },
];

const linkClass = ({ isActive }) =>
  `flex items-center gap-3 rounded-control px-3 py-2 text-sm font-medium transition-colors ${
    isActive ? "bg-teal-50 text-teal-800" : "text-ink-soft hover:bg-paper hover:text-ink"}`;

function NavList({ onNavigate }) {
  return (
    <nav aria-label="Main" className="space-y-6">
      {GROUPS.map((g) => (
        <div key={g.title}>
          <p className="mb-1.5 px-3 text-xs font-semibold text-ink-muted">{g.title}</p>
          <ul className="space-y-0.5">
            {g.items.map(({ to, label, icon: Icon, end }) => (
              <li key={to}>
                <NavLink to={to} end={end} className={linkClass} onClick={onNavigate}>
                  <Icon className="h-[18px] w-[18px]" aria-hidden /> {label}
                </NavLink>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </nav>
  );
}

export default function AppLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [sheet, setSheet] = useState(false);

  useEffect(() => { setSheet(false); window.scrollTo(0, 0); }, [location.pathname]);

  const signOut = () => { logout(); navigate("/", { replace: true }); };

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[17rem_1fr]">
      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-[70] focus:rounded-control focus:bg-white focus:px-3 focus:py-2">Skip to content</a>

      {/* Desktop sidebar */}
      <aside className="hidden border-r border-line bg-white lg:sticky lg:top-0 lg:flex lg:h-screen lg:flex-col">
        <div className="px-6 pb-6 pt-7"><Logo /></div>
        <div className="flex-1 overflow-y-auto px-3"><NavList /></div>
        <div className="border-t border-line p-4">
          <p className="truncate text-sm font-medium">{user.name}</p>
          <p className="truncate text-xs text-ink-muted">{user.email}</p>
          <button onClick={signOut} className="mt-3 flex items-center gap-2 text-sm font-medium text-ink-soft hover:text-ink">
            <LogOut className="h-4 w-4" aria-hidden /> Sign out
          </button>
        </div>
      </aside>

      {/* Mobile top bar */}
      <header className="sticky top-0 z-30 flex items-center justify-between border-b border-line bg-white px-4 py-3 lg:hidden">
        <Logo />
        <button onClick={() => setSheet(true)} className="rounded-control p-2 text-ink-soft hover:bg-paper" aria-label="Open menu"><Menu className="h-5 w-5" /></button>
      </header>

      <main id="main" className="min-w-0 px-4 pb-28 pt-6 sm:px-8 lg:px-12 lg:pb-16 lg:pt-10">
        <div className="mx-auto max-w-6xl"><Outlet /></div>
      </main>

      {/* Mobile bottom tabs */}
      <nav aria-label="Quick navigation" className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-5 border-t border-line bg-white pb-[env(safe-area-inset-bottom)] lg:hidden">
        {TABS.map(({ to, label, icon: Icon, end }) => (
          <NavLink key={to} to={to} end={end}
            className={({ isActive }) => `flex flex-col items-center gap-0.5 py-2.5 text-[11px] font-medium ${isActive ? "text-teal-700" : "text-ink-muted"}`}>
            <Icon className="h-5 w-5" aria-hidden /> {label}
          </NavLink>
        ))}
        <button onClick={() => setSheet(true)} className="flex flex-col items-center gap-0.5 py-2.5 text-[11px] font-medium text-ink-muted">
          <Menu className="h-5 w-5" aria-hidden /> More
        </button>
      </nav>

      {/* Mobile menu sheet */}
      {sheet && (
        <div className="fixed inset-0 z-50 bg-ink/40 lg:hidden" onMouseDown={(e) => e.target === e.currentTarget && setSheet(false)}>
          <div className="absolute inset-y-0 right-0 flex w-[19rem] max-w-full flex-col bg-white shadow-lift" role="dialog" aria-modal="true" aria-label="Menu">
            <div className="flex items-center justify-between border-b border-line px-5 py-4">
              <div className="min-w-0"><p className="truncate text-sm font-medium">{user.name}</p><p className="truncate text-xs text-ink-muted">{user.email}</p></div>
              <button onClick={() => setSheet(false)} className="rounded p-1.5 text-ink-muted hover:bg-paper" aria-label="Close menu"><X className="h-5 w-5" /></button>
            </div>
            <div className="flex-1 overflow-y-auto px-3 py-5"><NavList onNavigate={() => setSheet(false)} /></div>
            <button onClick={signOut} className="flex items-center gap-2 border-t border-line px-5 py-4 text-sm font-medium text-ink-soft"><LogOut className="h-4 w-4" aria-hidden /> Sign out</button>
          </div>
        </div>
      )}
    </div>
  );
}
