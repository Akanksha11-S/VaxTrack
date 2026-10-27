import { useState } from "react";
import { Link } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ArrowRight, Bell, FileDown, History, PlusCircle, ScanLine, ShieldCheck } from "lucide-react";
import PageHeader from "../components/PageHeader.jsx";
import { Panel, PanelHeader } from "../components/Panel.jsx";
import Button from "../components/Button.jsx";
import DosePips from "../components/DosePips.jsx";
import RecordFormModal from "../components/RecordFormModal.jsx";
import { Badge, ScheduleStatusBadge, VerificationBadge } from "../components/Badge.jsx";
import { EmptyState, ErrorNotice, Spinner, SCHEDULE_DISCLAIMER, Notice } from "../components/Feedback.jsx";
import { useAsync } from "../hooks/useAsync.js";
import { useAuth } from "../hooks/useAuth.jsx";
import { useToast } from "../hooks/useToast.jsx";
import { downloadReport } from "../utils/download.js";
import { api } from "../services/api.js";
import { STATUS, STATUS_ORDER, TONE_CLASS, doseText, formatAge, formatDate, greeting, relativeDays } from "../utils/format.js";

function Readout({ cards }) {
  const items = [
    { label: "Recorded doses", value: cards.total_doses, sub: `${cards.confirmed_doses} confirmed` },
    { label: "Schedule items completed", value: cards.completed_items, sub: `of ${cards.schedule_items} in your schedule` },
    { label: "Upcoming doses", value: cards.upcoming_doses, sub: "estimated, not appointments" },
    { label: "Records to check", value: cards.needs_verification, sub: cards.needs_verification ? "need your attention" : "all clear", warn: cards.needs_verification > 0 },
  ];
  return (
    <Panel as="dl" className="grid grid-cols-2 divide-line sm:grid-cols-4 sm:divide-x [&>div]:p-5 max-sm:[&>div:nth-child(n+3)]:border-t max-sm:[&>div]:border-line max-sm:[&>div:nth-child(even)]:border-l">
      {items.map((i) => (
        <div key={i.label}>
          <dt className="text-sm text-ink-muted">{i.label}</dt>
          <dd className={`mt-1 font-serif text-4xl font-semibold leading-none ${i.warn ? "text-amber-700" : ""}`}>{i.value}</dd>
          <dd className="mt-2 text-xs text-ink-muted">{i.sub}</dd>
        </div>
      ))}
    </Panel>
  );
}

function StatusBar({ counts }) {
  const total = counts.total || 1;
  return (
    <div>
      <div className="flex h-3 overflow-hidden rounded-full bg-paper ring-1 ring-inset ring-line" role="img"
        aria-label={STATUS_ORDER.map((k) => `${counts[k]} ${STATUS[k].label.toLowerCase()}`).join(", ")}>
        {STATUS_ORDER.map((k) => counts[k] > 0 && (
          <div key={k} className={TONE_CLASS[STATUS[k].tone].solid} style={{ width: `${(counts[k] / total) * 100}%` }} />
        ))}
      </div>
      <ul className="mt-3 flex flex-wrap gap-x-5 gap-y-1.5 text-xs text-ink-soft">
        {STATUS_ORDER.map((k) => (
          <li key={k} className="flex items-center gap-1.5">
            <span className={`h-2 w-2 rounded-full ${TONE_CLASS[STATUS[k].tone].dot}`} aria-hidden />
            {STATUS[k].label} <span className="font-semibold text-ink">{counts[k]}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function Dashboard() {
  const { user } = useAuth();
  const toast = useToast();
  const { data, loading, error, retry, reload } = useAsync(() => api.dashboard(), []);
  const [adding, setAdding] = useState(false);
  const [downloading, setDownloading] = useState(false);

  async function getReport() { setDownloading(true); await downloadReport(toast); setDownloading(false); }

  if (loading) return <Spinner label="Loading your record" />;
  if (error) return <ErrorNotice error={error} onRetry={retry} />;
  const { cards, counts, ledger, upcoming, attention, attention_total: attentionTotal, recent, per_year: perYear, schedule, age } = data;
  const firstName = user.name.split(" ")[0];
  const empty = cards.total_doses === 0;

  return (
    <div className="space-y-6">
      <PageHeader title={`${greeting()}, ${firstName}`}
        description={`Compared with the ${schedule?.name || "selected schedule"}. You're ${formatAge(age)} old.`}
        actions={<>
          <Button to="/app/upload" icon={ScanLine}>Upload a card</Button>
          <Button variant="secondary" icon={PlusCircle} onClick={() => setAdding(true)}>Add manually</Button>
        </>} />

      {empty && (
        <Notice>
          <strong className="font-semibold">Start with what you have.</strong> Upload a photo of a vaccination card, or add a dose by hand. Until you add records, schedule items without a record show as possibly missed. That only means nothing is recorded yet.
        </Notice>
      )}

      <Readout cards={cards} />

      <Panel aria-labelledby="overview">
        <PanelHeader id="overview" title="Vaccination overview" description={schedule ? `${schedule.name}, version ${schedule.version}` : undefined}
          action={<Button variant="quiet" to="/app/schedule" className="text-sm">Full schedule status <ArrowRight className="h-3.5 w-3.5" /></Button>} />
        <div className="grid gap-8 p-5 lg:grid-cols-[1.5fr_1fr]">
          <div className="space-y-5">
            <StatusBar counts={counts} />
            <ul className="row-divide rounded-control border border-line">
              {ledger.map((g) => (
                <li key={g.vaccine_id} className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1.5 px-4 py-2.5">
                  <span className="text-sm font-medium">{g.vaccine_name}</span>
                  <DosePips doses={g.doses} />
                </li>
              ))}
            </ul>
          </div>
          <div>
            <h3 className="mb-3 text-sm font-semibold">Doses recorded by year</h3>
            {perYear.length ? (
              <div className="h-52" role="img" aria-label={`Doses recorded per year: ${perYear.map((p) => `${p.year}: ${p.count}`).join(", ")}`}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={perYear} margin={{ top: 4, right: 4, left: -22, bottom: 0 }}>
                    <CartesianGrid vertical={false} stroke="#DCE6E3" />
                    <XAxis dataKey="year" tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: "#5B726F" }} />
                    <YAxis allowDecimals={false} tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: "#5B726F" }} />
                    <Tooltip cursor={{ fill: "#E7F4F1" }} contentStyle={{ borderRadius: 8, border: "1px solid #DCE6E3", fontSize: 12 }} formatter={(v) => [v, "Doses"]} />
                    <Bar dataKey="count" fill="#0E7C73" radius={[4, 4, 0, 0]} maxBarSize={36} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : <p className="rounded-control border border-dashed border-line-strong p-4 text-sm text-ink-muted">Dated records will appear here once you add some.</p>}
          </div>
        </div>
      </Panel>

      <div className="grid gap-6 lg:grid-cols-2">
        <Panel aria-labelledby="upcoming">
          <PanelHeader id="upcoming" title="Upcoming vaccinations" description="Estimates from your schedule, not appointments."
            action={<Button variant="quiet" to="/app/reminders" className="text-sm">Reminders</Button>} />
          {upcoming.length ? (
            <ul className="row-divide">
              {upcoming.map((u) => (
                <li key={`${u.vaccine_id}-${u.dose}`} className="flex items-center justify-between gap-3 px-5 py-3.5">
                  <div className="min-w-0"><p className="truncate text-sm font-medium">{u.vaccine_name}</p><p className="text-xs text-ink-muted">{u.dose_label}</p></div>
                  <div className="shrink-0 text-right"><p className="text-sm font-medium">{formatDate(u.estimated_date)}</p><p className="text-xs text-ink-muted">{relativeDays(u.estimated_date)}</p></div>
                </li>
              ))}
            </ul>
          ) : <EmptyState icon={ShieldCheck} title="Nothing coming up">No further doses are estimated for your age on this schedule.</EmptyState>}
        </Panel>

        <Panel aria-labelledby="attention">
          <PanelHeader id="attention" title="Records that need attention" description={attentionTotal ? `${attentionTotal} to review` : undefined}
            action={attentionTotal > 0 && <Button variant="quiet" to="/app/history" className="text-sm">Review all</Button>} />
          {attention.length ? (
            <ul className="row-divide">
              {attention.map((r) => (
                <li key={r.id} className="px-5 py-3.5">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="text-sm font-medium">{r.vaccine_name}{r.dose_number !== null && <span className="font-normal text-ink-muted"> - {doseText(r.dose_number).toLowerCase()}</span>}</p>
                    <Badge tone={r.has_error ? "red" : "amber"}>{r.has_error ? "Check this record" : "Needs review"}</Badge>
                  </div>
                  <p className="mt-1 text-xs text-ink-muted">{r.flags[0].message}{r.flags.length > 1 && ` (+${r.flags.length - 1} more)`}</p>
                </li>
              ))}
            </ul>
          ) : <EmptyState icon={ShieldCheck} title="No records need attention">Every saved record is confirmed and consistent.</EmptyState>}
        </Panel>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.6fr_1fr]">
        <Panel aria-labelledby="recent">
          <PanelHeader id="recent" title="Recent records" action={<Button variant="quiet" to="/app/history" className="text-sm">View all</Button>} />
          {recent.length ? (
            <ul className="row-divide">
              {recent.map((r) => (
                <li key={r.id} className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1.5 px-5 py-3.5">
                  <div className="min-w-0"><p className="truncate text-sm font-medium">{r.vaccine_name}</p>
                    <p className="text-xs text-ink-muted">{doseText(r.dose_number)} - {formatDate(r.vaccination_date)}</p></div>
                  <VerificationBadge record={r} />
                </li>
              ))}
            </ul>
          ) : <EmptyState icon={History} title="No records yet" action={<Button to="/app/upload" size="sm" icon={ScanLine}>Upload a card</Button>}>
            Records you save will be listed here.</EmptyState>}
        </Panel>

        <Panel aria-labelledby="actions">
          <PanelHeader id="actions" title="Quick actions" />
          <div className="flex flex-col gap-2 p-4">
            <Button to="/app/upload" icon={ScanLine} className="justify-start">Upload vaccination card</Button>
            <Button variant="secondary" icon={PlusCircle} className="justify-start" onClick={() => setAdding(true)}>Add vaccination manually</Button>
            <Button variant="secondary" to="/app/history" icon={History} className="justify-start">View vaccination history</Button>
            <Button variant="secondary" to="/app/reminders" icon={Bell} className="justify-start">View reminders</Button>
            <Button variant="secondary" icon={FileDown} loading={downloading} className="justify-start" onClick={getReport}>Download vaccination report</Button>
          </div>
        </Panel>
      </div>

      <p className="text-xs leading-relaxed text-ink-muted">{SCHEDULE_DISCLAIMER}</p>
      <RecordFormModal open={adding} onClose={() => setAdding(false)} onSaved={reload} />
    </div>
  );
}
