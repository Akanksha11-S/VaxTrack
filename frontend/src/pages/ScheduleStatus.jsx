import { useState } from "react";
import { Link } from "react-router-dom";
import { ExternalLink } from "lucide-react";
import PageHeader from "../components/PageHeader.jsx";
import { Panel } from "../components/Panel.jsx";
import { ScheduleStatusBadge } from "../components/Badge.jsx";
import { ErrorNotice, Notice, Spinner } from "../components/Feedback.jsx";
import { useAsync } from "../hooks/useAsync.js";
import { api } from "../services/api.js";
import { STATUS, STATUS_ORDER, TONE_CLASS, formatAge, formatDate } from "../utils/format.js";

export default function ScheduleStatus() {
  const { data, loading, error, retry } = useAsync(() => api.scheduleStatus(), []);
  const [filter, setFilter] = useState("all");
  if (loading) return <Spinner label="Comparing your records with the schedule" />;
  if (error) return <ErrorNotice error={error} onRetry={retry} />;
  const { schedule, counts, vaccines, disclaimer, age } = data;
  const visible = vaccines
    .map((v) => ({ ...v, doses: v.doses.filter((d) => filter === "all" || d.status === filter) }))
    .filter((v) => v.doses.length);

  return (
    <div className="space-y-6">
      <PageHeader title="Schedule status" description={`How your confirmed records compare with the ${schedule.name}. You're ${formatAge(age)} old.`} />

      <Panel className="flex flex-wrap items-start justify-between gap-4 p-5">
        <div>
          <p className="font-medium">{schedule.name}</p>
          <p className="mt-1 text-sm text-ink-muted">Version {schedule.version}</p>
          <p className="text-sm text-ink-muted">Source: {schedule.source}</p>
          {schedule.description && <p className="mt-2 max-w-2xl text-sm leading-relaxed text-ink-soft">{schedule.description}</p>}
        </div>
        <div className="flex flex-col items-start gap-2 text-sm font-medium text-teal-700 sm:items-end">
          {schedule.source_url && <a href={schedule.source_url} target="_blank" rel="noreferrer noopener" className="inline-flex items-center gap-1.5 hover:underline">View source <ExternalLink className="h-3.5 w-3.5" aria-hidden /></a>}
          <Link to="/app/profile" className="hover:underline">Change schedule</Link>
        </div>
      </Panel>

      <Notice>{disclaimer}</Notice>

      <div className="flex flex-wrap gap-2" role="group" aria-label="Filter by status">
        <button onClick={() => setFilter("all")} aria-pressed={filter === "all"}
          className={`rounded-full border px-3.5 py-1.5 text-sm font-medium ${filter === "all" ? "border-teal-600 bg-teal-600 text-white" : "border-line-strong bg-white text-ink-soft hover:bg-paper"}`}>All ({counts.total})</button>
        {STATUS_ORDER.map((k) => (
          <button key={k} onClick={() => setFilter(k)} aria-pressed={filter === k} disabled={counts[k] === 0}
            className={`flex items-center gap-2 rounded-full border px-3.5 py-1.5 text-sm font-medium disabled:opacity-45 ${filter === k ? "border-teal-600 bg-teal-50 text-teal-800" : "border-line-strong bg-white text-ink-soft hover:bg-paper"}`}>
            <span className={`h-2 w-2 rounded-full ${TONE_CLASS[STATUS[k].tone].dot}`} aria-hidden />{STATUS[k].label} ({counts[k]})
          </button>
        ))}
      </div>

      <div className="space-y-4">
        {visible.map((v) => (
          <Panel key={v.vaccine_id} aria-labelledby={`v-${v.vaccine_id}`}>
            <h2 id={`v-${v.vaccine_id}`} className="border-b border-line px-5 py-3.5 font-serif text-lg font-semibold">{v.vaccine_name}</h2>
            <ul className="row-divide">
              {v.doses.map((d) => (
                <li key={d.dose} className="grid gap-x-6 gap-y-1.5 px-5 py-4 md:grid-cols-[14rem_1fr]">
                  <div>
                    <p className="text-sm font-medium">{d.dose_label}</p>
                    <p className="text-xs text-ink-muted">Recommended at {d.age_label}</p>
                    <div className="mt-2"><ScheduleStatusBadge status={d.status} /></div>
                  </div>
                  <div className="text-sm leading-relaxed">
                    <p className="text-ink-soft">{d.explanation}</p>
                    <p className="mt-1 text-xs text-ink-muted">
                      {d.record_date ? `Recorded ${formatDate(d.record_date)}` : d.estimated_date ? `Estimated ${formatDate(d.estimated_date)}` : ""}
                      {d.notes && `${d.record_date || d.estimated_date ? " - " : ""}${d.notes}`}
                    </p>
                  </div>
                </li>
              ))}
            </ul>
          </Panel>
        ))}
      </div>
    </div>
  );
}
