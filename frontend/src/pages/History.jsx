import { useState } from "react";
import { History as HistoryIcon, Pencil, PlusCircle, ScanLine, Trash2 } from "lucide-react";
import PageHeader from "../components/PageHeader.jsx";
import { Panel } from "../components/Panel.jsx";
import Button from "../components/Button.jsx";
import { VerificationBadge } from "../components/Badge.jsx";
import { ConfirmDialog } from "../components/Modal.jsx";
import RecordFormModal from "../components/RecordFormModal.jsx";
import RecordFilters, { applyFilters } from "../components/RecordFilters.jsx";
import { EmptyState, ErrorNotice, Spinner } from "../components/Feedback.jsx";
import { useAsync } from "../hooks/useAsync.js";
import { useToast } from "../hooks/useToast.jsx";
import { api } from "../services/api.js";
import { doseText, formatDate } from "../utils/format.js";

export function FlagList({ record }) {
  const flags = record.flags.filter((f) => f.code !== "unverified");
  if (!flags.length) return null;
  return <ul className="mt-1 space-y-0.5 text-xs text-amber-700">{flags.map((f) => <li key={f.code} className={f.severity === "error" ? "font-medium text-rose-700" : ""}>{f.message}</li>)}</ul>;
}

export function RowActions({ record, onEdit, onDelete }) {
  return (
    <div className="flex justify-end gap-1">
      <button onClick={() => onEdit(record)} className="rounded p-2 text-ink-muted hover:bg-teal-50 hover:text-teal-700" aria-label={`Edit ${record.vaccine_name}`}><Pencil className="h-4 w-4" /></button>
      <button onClick={() => onDelete(record)} className="rounded p-2 text-ink-muted hover:bg-rose-50 hover:text-rose-700" aria-label={`Delete ${record.vaccine_name}`}><Trash2 className="h-4 w-4" /></button>
    </div>
  );
}

export function useRecordEditing(reload) {
  const toast = useToast();
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(false);
  const [deleting, setDeleting] = useState(null);
  const [busy, setBusy] = useState(false);
  async function confirmDelete() {
    setBusy(true);
    try { await api.deleteRecord(deleting.id); toast.success("Record deleted."); setDeleting(null); reload(); }
    catch (err) { toast.error(err.message); } finally { setBusy(false); }
  }
  const dialogs = (
    <>
      <RecordFormModal open={form} record={editing} onClose={() => setForm(false)} onSaved={reload} />
      <ConfirmDialog open={Boolean(deleting)} title="Delete this record?" onClose={() => setDeleting(null)} onConfirm={confirmDelete} loading={busy}>
        <p>{deleting?.vaccine_name}{deleting?.dose_number != null && `, dose ${deleting.dose_number}`} ({formatDate(deleting?.vaccination_date)}) will be removed. Your schedule status and reminders will update.</p>
      </ConfirmDialog>
    </>
  );
  return { dialogs, add: () => { setEditing(null); setForm(true); }, edit: (r) => { setEditing(r); setForm(true); }, del: setDeleting };
}

export default function History() {
  const { data, loading, error, retry, reload } = useAsync(() => api.listRecords(), []);
  const [filters, setFilters] = useState({ q: "", vaccine: "", year: "", status: "" });
  const ed = useRecordEditing(reload);

  if (loading) return <Spinner label="Loading your history" />;
  if (error) return <ErrorNotice error={error} onRetry={retry} />;
  const records = [...data].sort((a, b) => (b.vaccination_date || "").localeCompare(a.vaccination_date || "") || b.id - a.id);
  const shown = applyFilters(records, filters);
  const filtering = filters.q || filters.vaccine || filters.year || filters.status;

  return (
    <div className="space-y-6">
      <PageHeader title="Vaccination history" description="Every record you've saved, from uploaded cards and manual entries."
        actions={<><Button to="/app/upload" icon={ScanLine}>Upload a card</Button><Button variant="secondary" icon={PlusCircle} onClick={ed.add}>Add manually</Button></>} />

      {records.length === 0 ? (
        <Panel><EmptyState icon={HistoryIcon} title="No records yet"
          action={<div className="flex gap-2"><Button to="/app/upload" icon={ScanLine} size="sm">Upload a card</Button><Button variant="secondary" size="sm" icon={PlusCircle} onClick={ed.add}>Add manually</Button></div>}>
          Upload a vaccination card or add a dose by hand to start your record.</EmptyState></Panel>
      ) : (
        <>
          <RecordFilters records={records} filters={filters} onChange={setFilters} />
          <p className="text-sm text-ink-muted" aria-live="polite">Showing {shown.length} of {records.length} record{records.length === 1 ? "" : "s"}.</p>
          {shown.length === 0 ? (
            <Panel><EmptyState title="No records match these filters" action={<Button variant="secondary" size="sm" onClick={() => setFilters({ q: "", vaccine: "", year: "", status: "" })}>Clear filters</Button>}>
              {filtering && "Try a different search or clear the filters."}</EmptyState></Panel>
          ) : (
            <Panel className="overflow-hidden">
              <table className="hidden w-full text-sm md:table">
                <thead><tr className="border-b border-line bg-paper text-left text-xs text-ink-muted">
                  <th className="px-5 py-3 font-medium">Vaccine</th><th className="px-3 py-3 font-medium">Dose</th><th className="px-3 py-3 font-medium">Date given</th>
                  <th className="px-3 py-3 font-medium">Status</th><th className="px-3 py-3 font-medium">Source</th><th className="px-5 py-3"><span className="sr-only">Actions</span></th></tr></thead>
                <tbody>
                  {shown.map((r) => (
                    <tr key={r.id} className="border-b border-line last:border-0 align-top">
                      <td className="px-5 py-3.5"><p className="font-medium">{r.vaccine_name}</p><FlagList record={r} />{r.notes && <p className="mt-1 text-xs text-ink-muted">{r.notes}</p>}</td>
                      <td className="px-3 py-3.5 text-ink-soft">{r.dose_number === null ? "Not recorded" : r.dose_number}</td>
                      <td className={`px-3 py-3.5 ${r.vaccination_date ? "" : "text-ink-muted"}`}>{formatDate(r.vaccination_date)}</td>
                      <td className="px-3 py-3.5"><VerificationBadge record={r} /></td>
                      <td className="max-w-[10rem] truncate px-3 py-3.5 text-ink-muted" title={r.source_document || ""}>{r.source_document || (r.source_type === "manual" ? "Entered manually" : "Uploaded card")}</td>
                      <td className="px-5 py-2.5"><RowActions record={r} onEdit={ed.edit} onDelete={ed.del} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <ul className="row-divide md:hidden">
                {shown.map((r) => (
                  <li key={r.id} className="space-y-1.5 px-4 py-4">
                    <div className="flex items-start justify-between gap-2"><p className="font-medium">{r.vaccine_name}</p><RowActions record={r} onEdit={ed.edit} onDelete={ed.del} /></div>
                    <p className="text-sm text-ink-muted">{doseText(r.dose_number)} - {formatDate(r.vaccination_date)}</p>
                    <VerificationBadge record={r} /><FlagList record={r} />
                  </li>
                ))}
              </ul>
            </Panel>
          )}
        </>
      )}
      {ed.dialogs}
    </div>
  );
}
