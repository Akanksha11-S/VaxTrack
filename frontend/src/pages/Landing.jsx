import { Link } from "react-router-dom";
import Logo from "../components/Logo.jsx";
import Button from "../components/Button.jsx";
import DosePips from "../components/DosePips.jsx";
import { Badge } from "../components/Badge.jsx";
import { useAuth } from "../hooks/useAuth.jsx";

const SAMPLE = [
  { vaccine: "BCG", doses: [{ dose: 1, dose_label: "BCG", status: "recorded" }], note: "14 Mar 2020", badge: ["green", "Confirmed"] },
  { vaccine: "Oral polio (OPV)", doses: [
    { dose: 0, dose_label: "Birth dose", status: "recorded" }, { dose: 1, dose_label: "OPV-1", status: "recorded" },
    { dose: 2, dose_label: "OPV-2", status: "recorded" }, { dose: 3, dose_label: "OPV-3", status: "needs_verification" },
  ], note: "OPV-3 read from card", badge: ["amber", "Needs your check"] },
  { vaccine: "Measles-Rubella", doses: [
    { dose: 1, dose_label: "MR-1", status: "recorded" }, { dose: 2, dose_label: "MR-2", status: "upcoming" },
  ], note: "MR-2 estimated Jun 2026", badge: ["amber", "Upcoming"] },
  { vaccine: "Japanese encephalitis", doses: [
    { dose: 1, dose_label: "JE-1", status: "not_enough_information" },
  ], note: "Depends on where you live", badge: ["neutral", "Not enough information"] },
];

const STEPS = [
  ["Upload your card", "Take a photo or add a scanned PDF. VaxTrack reads the text and suggests vaccine names, dates and dose numbers."],
  ["Check what was read", "Every suggestion lands in an editable table. Fix mistakes, fill gaps, and confirm only the rows you trust."],
  ["See what's next", "Confirmed records are compared with a published schedule, and the doses that may be coming up appear as reminders."],
];

export default function Landing() {
  const { user } = useAuth();
  return (
    <div className="min-h-screen">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
        <Logo />
        <nav className="flex items-center gap-2" aria-label="Account">
          {user ? <Button to="/app" size="sm">Open dashboard</Button> : (
            <>
              <Link to="/login" className="rounded-control px-3 py-2 text-sm font-medium text-ink-soft hover:text-ink">Sign in</Link>
              <Button to="/register" size="sm">Create account</Button>
            </>
          )}
        </nav>
      </header>

      <main>
        <section className="mx-auto grid max-w-6xl items-center gap-12 px-6 pb-20 pt-10 lg:grid-cols-[1.05fr_1fr] lg:pt-16">
          <div>
            <h1 className="font-serif text-[2.4rem] font-semibold leading-[1.1] tracking-tight sm:text-5xl">
              Your vaccination history, in one place you can trust.
            </h1>
            <p className="mt-5 max-w-xl text-lg leading-relaxed text-ink-soft">
              Scan an old vaccination card, check what VaxTrack read from it, and see which doses are recorded, which may be coming up, and which records still need a second look.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Button to={user ? "/app" : "/register"} size="lg">{user ? "Open dashboard" : "Create a free account"}</Button>
              {!user && <Button to="/login" variant="secondary" size="lg">Sign in</Button>}
            </div>
            <p className="mt-4 text-sm text-ink-muted">Built for personal record keeping. VaxTrack does not give medical advice.</p>
          </div>

          {/* A sample ledger page, built from the same components as the dashboard */}
          <figure aria-label="Example of a VaxTrack record">
            <div className="rounded-panel border border-line bg-white p-1.5 shadow-lift">
              <div className="rounded-[10px] border border-line px-5 py-4">
                <div className="flex items-baseline justify-between border-b border-line pb-3">
                  <p className="font-serif text-lg font-semibold">Immunisation record</p>
                  <p className="text-xs text-ink-muted">Sample data</p>
                </div>
                <ul className="row-divide">
                  {SAMPLE.map((r) => (
                    <li key={r.vaccine} className="grid grid-cols-[1fr_auto] items-center gap-x-4 gap-y-1.5 py-3.5">
                      <div><p className="text-sm font-medium">{r.vaccine}</p><p className="text-xs text-ink-muted">{r.note}</p></div>
                      <Badge tone={r.badge[0]}>{r.badge[1]}</Badge>
                      <div className="col-span-2"><DosePips doses={r.doses} /></div>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
            <figcaption className="mt-3 text-center text-xs text-ink-muted">Filled squares are recorded doses. Outlined squares are estimates or need checking.</figcaption>
          </figure>
        </section>

        <section className="border-y border-line bg-white" aria-labelledby="how">
          <div className="mx-auto max-w-6xl px-6 py-16">
            <h2 id="how" className="font-serif text-2xl font-semibold">How it works</h2>
            <ol className="mt-8 grid gap-8 md:grid-cols-3 md:gap-0 md:divide-x md:divide-line">
              {STEPS.map(([title, body], i) => (
                <li key={title} className="md:px-8 md:first:pl-0 md:last:pr-0">
                  <p className="font-serif text-3xl font-semibold text-teal-600">{i + 1}</p>
                  <h3 className="mt-2 font-semibold">{title}</h3>
                  <p className="mt-1.5 text-sm leading-relaxed text-ink-muted">{body}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section className="mx-auto grid max-w-6xl gap-10 px-6 py-16 md:grid-cols-2" aria-labelledby="limits">
          <div>
            <h2 id="limits" className="font-serif text-2xl font-semibold">What VaxTrack won't do</h2>
            <p className="mt-3 max-w-md leading-relaxed text-ink-muted">Vaccine records are personal and the schedule that applies to you depends on where you live and your health. So the app is deliberately cautious.</p>
          </div>
          <dl className="space-y-5 text-sm leading-relaxed">
            {[
              ["It won't call a dose missed.", "With no record, the strongest label is \"Possibly missed\". The record may simply not have been added yet."],
              ["It won't trust a scan on its own.", "Text read from a card stays marked as not confirmed until you confirm it."],
              ["It won't promise appointments.", "Reminder dates are estimates from the schedule you choose, and are labelled that way."],
              ["It won't tell you what to take.", "Explanations are educational. A healthcare provider decides what is right for you."],
            ].map(([t, d]) => <div key={t}><dt className="font-semibold">{t}</dt><dd className="text-ink-muted">{d}</dd></div>)}
          </dl>
        </section>
      </main>

      <footer className="border-t border-line bg-white">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-6 py-6 text-sm text-ink-muted">
          <Logo />
          <p className="max-w-xl">VaxTrack is an educational college project. It is not a medical device and not an official vaccination certificate.</p>
        </div>
      </footer>
    </div>
  );
}
