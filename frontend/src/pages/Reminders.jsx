import { useState } from "react";
import { Bell, BellOff, Check, CheckCheck, RefreshCw, Undo2, X } from "lucide-react";
import PageHeader from "../components/PageHeader.jsx";
import { Panel, PanelHeader } from "../components/Panel.jsx";
import Button from "../components/Button.jsx";
import { Badge } from "../components/Badge.jsx";
import { SelectField, Toggle } from "../components/Form.jsx";
import { EmptyState, ErrorNotice, Notice, Spinner } from "../components/Feedback.jsx";
import { useAsync } from "../hooks/useAsync.js";
import { useAuth } from "../hooks/useAuth.jsx";
import { useToast } from "../hooks/useToast.jsx";
import { api } from "../services/api.js";
import { doseText, formatDate, relativeDays } from "../utils/format.js";

function ReminderRow({ r, onSet, busy }) {
  const closed = r.status === "completed" || r.status === "dismissed";
  return (
    <li className="grid gap-3 px-5 py-4 md:grid-cols-[1fr_auto] md:items-center">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <p className="font-medium">{r.vaccine_name}</p>
          <span className="text-sm text-ink-muted">{doseText(r.dose_number)}</span>
          {r.is_due_soon && <Badge tone="amber">Due soon</Badge>}
          {r.date_source === "card" && <Badge tone="blue">From card</Badge>}
          {r.needs_confirmation && <Badge tone="amber">Estimate — confirm</Badge>}
          {r.status === "acknowledged" && <Badge tone="blue">Acknowledged</Badge>}
          {r.status === "completed" && <Badge tone="green">Completed</Badge>}
          {r.status === "dismissed" && <Badge>Dismissed</Badge>}
        </div>
        <p className="mt-1 text-sm"><span className="font-medium">Estimated {formatDate(r.estimated_date)}</span> <span className="text-ink-muted">({relativeDays(r.estimated_date)})</span></p>
        <p className="mt-1 max-w-2xl text-sm leading-relaxed text-ink-muted">{r.reason}</p>
      </div>
      <div className="flex flex-wrap gap-2 md:justify-end">
        {!closed && r.status !== "acknowledged" && <Button size="sm" variant="secondary" icon={Check} disabled={busy} onClick={() => onSet(r, "acknowledged")}>Acknowledge</Button>}
        {!closed && <Button size="sm" variant="secondary" icon={CheckCheck} disabled={busy} onClick={() => onSet(r, "completed")}>Mark done</Button>}
        {!closed && <Button size="sm" variant="ghost" icon={X} disabled={busy} onClick={() => onSet(r, "dismissed")}>Dismiss</Button>}
        {closed && <Button size="sm" variant="ghost" icon={Undo2} disabled={busy} onClick={() => onSet(r, "pending")}>Restore</Button>}
      </div>
    </li>
  );
}

export default function Reminders() {
  const { user, setUser } = useAuth();
  const toast = useToast();
  const { data, loading, error, retry, reload } = useAsync(() => api.reminders(), []);
  const [busy, setBusy] = useState(false);

  async function setStatus(r, status) {
    setBusy(true);
    try {
      await api.updateReminder(r.id, status); await reload();
      toast.success({ acknowledged: "Reminder acknowledged.", completed: "Marked as done. Add the record to your history so it counts toward your schedule.", dismissed: "Reminder dismissed.", pending: "Reminder restored." }[status]);
    } catch (e) { toast.error(e.message); } finally { setBusy(false); }
  }
  async function savePrefs(patch) {
    try { setUser(await api.updateProfile(patch)); await reload(); toast.success("Reminder settings saved."); } catch (e) { toast.error(e.message); }
  }
  async function recalc() {
    setBusy(true);
    try { await api.recalcReminders(); await reload(); toast.success("Reminders recalculated from your latest records."); } catch (e) { toast.error(e.message); } finally { setBusy(false); }
  }

  if (loading) return <Spinner label="Loading reminders" />;
  if (error) return <ErrorNotice error={error} onRetry={retry} />;
  const list = data.reminders;
  const groups = [
    ["Due soon", list.filter((r) => r.is_due_soon)],
    ["Later", list.filter((r) => r.status === "pending" && !r.is_due_soon)],
    ["Acknowledged", list.filter((r) => r.status === "acknowledged")],
    ["Done or dismissed", list.filter((r) => r.status === "completed" || r.status === "dismissed")],
  ].filter(([, items]) => items.length);

  return (
    <div className="space-y-6">
      <PageHeader title="Reminders" description="Card-specific due dates take priority. If a card has no due date, VaxTrack can show a tentative schedule estimate for you to confirm."
        actions={<Button variant="secondary" icon={RefreshCw} loading={busy} onClick={recalc}>Recalculate</Button>} />
      <Notice>{data.notice}</Notice>
      {!data.email_enabled && <Notice tone="warn">Email reminders are not active yet. Configure SMTP_HOST, SMTP_PORT, SMTP_FROM, and your mail credentials in the backend .env file; in-app reminders will continue to work.</Notice>}
      {!user.reminders_enabled && <Notice tone="warn"><span className="flex items-center gap-2"><BellOff className="h-4 w-4" aria-hidden /> Reminders are paused, so nothing is flagged as due soon. Turn them back on below.</span></Notice>}

      <Panel aria-labelledby="prefs">
        <PanelHeader id="prefs" title="Reminder settings" />
        <div className="grid gap-5 p-5 md:grid-cols-2">
          <Toggle checked={user.reminders_enabled} onChange={(v) => savePrefs({ reminders_enabled: v })} label="Show reminders" description="Flag doses as due soon on the dashboard and this page." />
          <SelectField label="Remind me" value={user.reminder_lead_days} onChange={(e) => savePrefs({ reminder_lead_days: Number(e.target.value) })} disabled={!user.reminders_enabled}
            hint="How long before the estimated date a reminder is marked as due soon.">
            {[3, 7, 14, 30].map((d) => <option key={d} value={d}>{d} days before</option>)}
          </SelectField>
        </div>
      </Panel>

      {groups.length === 0 ? (
        <Panel><EmptyState icon={Bell} title="No reminders right now">When a dose is estimated for the coming year, it will appear here. Confirm more records to keep estimates accurate.</EmptyState></Panel>
      ) : groups.map(([title, items]) => (
        <Panel key={title} aria-label={title}>
          <PanelHeader title={title} description={`${items.length} reminder${items.length === 1 ? "" : "s"}`} />
          <ul className="row-divide">{items.map((r) => <ReminderRow key={r.id} r={r} onSet={setStatus} busy={busy} />)}</ul>
        </Panel>
      ))}
    </div>
  );
}
