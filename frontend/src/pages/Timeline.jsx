import { useState } from "react";
import { CalendarClock, Pencil, PlusCircle, Route as RouteIcon, Trash2 } from "lucide-react";
import PageHeader from "../components/PageHeader.jsx";
import { Panel } from "../components/Panel.jsx";
import Button from "../components/Button.jsx";
import { Badge, ScheduleStatusBadge, VerificationBadge } from "../components/Badge.jsx";
import RecordFilters, { applyFilters } from "../components/RecordFilters.jsx";
import { EmptyState, ErrorNotice, Notice, Spinner } from "../components/Feedback.jsx";
import { FlagList, useRecordEditing } from "./History.jsx";
import { useAsync } from "../hooks/useAsync.js";
import { api } from "../services/api.js";
import { doseText, formatDate, parseISO, relativeDays } from "../utils/format.js";

function ageAt(dob, iso) {
  const d = parseISO(iso), b = parseISO(dob);
  if (!d || !b) return "";
  let months = (d.getFullYear() - b.getFullYear()) * 12 + d.getMonth() - b.getMonth();
  if (d.getDate() < b.getDate()) months -= 1;
  if (months < 1) return `${Math.max(0, Math.round((d - b) / 86400000))} days old`;
  if (months < 24) return `${months} months old`;
  return `${Math.floor(months / 12)} years old`;
}

function Entry({ record, dob, onEdit, onDelete }) {
  const confirmed = record.verification_status === "confirmed" && !record.has_error;
  return (
    <li className="relative pb-7 pl-8 last:pb-0">
      <span className={`absolute left-0 top-1.5 h-[15px] w-[15px] rounded-full border-2 ${confirmed ? "border-teal-600 bg-teal-600" : "border-amber-500 bg-white"}`} aria-hidden />
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="font-medium">{record.vaccine_name} <span className="font-normal text-ink-muted">- {doseText(record.dose_number).toLowerCase()}</span></p>
          <p className="text-sm text-ink-muted">{formatDate(record.vaccination_date)}{record.vaccination_date && dob && ` - ${ageAt(dob, record.vaccination_date)}`}</p>
          <FlagList record={record} />
        </div>
        <div className="flex items-center gap-1"><VerificationBadge record={record} />
          <button onClick={() => onEdit(record)} className="rounded p-2 text-ink-muted hover:bg-teal-50 hover:text-teal-700" aria-label={`Edit ${record.vaccine_name}`}><Pencil className="h-4 w-4" /></button>
          <button onClick={() => onDelete(record)} className="rounded p-2 text-ink-muted hover:bg-rose-50 hover:text-rose-700" aria-label={`Delete ${record.vaccine_name}`}><Trash2 className="h-4 w-4" /></button>
        </div>
      </div>
    </li>
  );
}

function Rail({ children }) {
  return <ol className="relative ml-1.5 border-l-2 border-line">{children}</ol>;
}

export default function Timeline() {
  const { data, loading, error, retry, reload } = useAsync(() => api.timeline(), []);
  const [filters, setFilters] = useState({ q: "", vaccine: "", year: "", status: "" });
  const ed = useRecordEditing(reload);

  if (loading) return <Spinner label="Building your timeline" />;
  if (error) return <ErrorNotice error={error} onRetry={retry} />;

  const all = [...data.history, ...data.undated];
  const history = applyFilters(data.history, filters);
  const undated = applyFilters(data.undated, filters);
  const upcoming = data.upcoming.filter((u) => (!filters.q || u.vaccine_name.toLowerCase().includes(filters.q.toLowerCase())) && (!filters.vaccine || u.vaccine_name === filters.vaccine) && !filters.year && !filters.status);
  const byYear = history.reduce((acc, r) => { const y = r.vaccination_date.slice(0, 4); (acc[y] ||= []).push(r); return acc; }, {});
  const years = Object.keys(byYear).sort((a, b) => b - a);

  return (
    <div className="space-y-6">
      <PageHeader title="Vaccination timeline" description="Your history in date order, with estimated upcoming doses kept separate."
        actions={<Button variant="secondary" icon={PlusCircle} onClick={ed.add}>Add manually</Button>} />

      {all.length === 0 && upcoming.length === 0 ? (
        <Panel><EmptyState icon={RouteIcon} title="Your timeline is empty" action={<Button size="sm" to="/app/upload">Upload a card</Button>}>Add records to see them laid out by date.</EmptyState></Panel>
      ) : (
        <>
          <RecordFilters records={all} filters={filters} onChange={setFilters} />
          <div className="flex flex-wrap items-center gap-x-5 gap-y-1 text-xs text-ink-soft" aria-label="Key">
            <span className="flex items-center gap-1.5"><span className="h-3 w-3 rounded-full border-2 border-teal-600 bg-teal-600" aria-hidden />Confirmed</span>
            <span className="flex items-center gap-1.5"><span className="h-3 w-3 rounded-full border-2 border-amber-500 bg-white" aria-hidden />Not confirmed or needs checking</span>
            <span className="flex items-center gap-1.5"><span className="h-3 w-3 rounded-full border-2 border-dashed border-azure-600 bg-white" aria-hidden />Estimated, not an appointment</span>
          </div>

          {upcoming.length > 0 && (
            <Panel className="p-5" aria-labelledby="est">
              <h2 id="est" className="font-serif text-lg font-semibold">Estimated upcoming doses</h2>
              <p className="mb-5 mt-0.5 text-sm text-ink-muted">Calculated from your date of birth and schedule. Dates are estimates.</p>
              <ol className="relative ml-1.5 border-l-2 border-dashed border-azure-100">
                {upcoming.map((u) => (
                  <li key={`${u.vaccine_id}-${u.dose}`} className="relative pb-5 pl-8 last:pb-0">
                    <span className="absolute left-0 top-1.5 h-[15px] w-[15px] rounded-full border-2 border-dashed border-azure-600 bg-white" style={{ marginLeft: -1 }} aria-hidden />
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <div><p className="font-medium">{u.vaccine_name} <span className="font-normal text-ink-muted">- {u.dose_label}</span></p>
                        <p className="text-sm text-ink-muted">Around {formatDate(u.estimated_date)} ({relativeDays(u.estimated_date)})</p></div>
                      <ScheduleStatusBadge status={u.status} />
                    </div>
                  </li>
                ))}
              </ol>
            </Panel>
          )}

          {years.length === 0 && undated.length === 0 && (
            <Panel><EmptyState title="No records match these filters" action={<Button variant="secondary" size="sm" onClick={() => setFilters({ q: "", vaccine: "", year: "", status: "" })}>Clear filters</Button>} /></Panel>
          )}

          {years.map((y) => (
            <Panel key={y} className="p-5" aria-label={`Records from ${y}`}>
              <h2 className="mb-5 font-serif text-lg font-semibold">{y}</h2>
              <Rail>{byYear[y].map((r) => <Entry key={r.id} record={r} dob={data.date_of_birth} onEdit={ed.edit} onDelete={ed.del} />)}</Rail>
            </Panel>
          ))}

          {undated.length > 0 && (
            <Panel className="p-5" aria-labelledby="undated">
              <h2 id="undated" className="font-serif text-lg font-semibold">Date not recorded</h2>
              <p className="mb-5 mt-0.5 text-sm text-ink-muted">These doses can't be placed on the timeline. Edit them to add a date.</p>
              <Rail>{undated.map((r) => <Entry key={r.id} record={r} dob={null} onEdit={ed.edit} onDelete={ed.del} />)}</Rail>
            </Panel>
          )}
        </>
      )}
      {ed.dialogs}
    </div>
  );
}
