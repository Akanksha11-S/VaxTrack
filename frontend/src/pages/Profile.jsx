import { useEffect, useState } from "react";
import { ExternalLink } from "lucide-react";
import PageHeader from "../components/PageHeader.jsx";
import { Panel, PanelHeader } from "../components/Panel.jsx";
import Button from "../components/Button.jsx";
import { SelectField, TextField, Toggle } from "../components/Form.jsx";
import { ErrorNotice, Notice, Spinner } from "../components/Feedback.jsx";
import { useAsync } from "../hooks/useAsync.js";
import { useAuth } from "../hooks/useAuth.jsx";
import { useToast } from "../hooks/useToast.jsx";
import { api } from "../services/api.js";
import { todayISO } from "../utils/format.js";

export default function Profile() {
  const { user, setUser } = useAuth();
  const toast = useToast();
  const schedules = useAsync(() => api.scheduleOptions(), []);
  const [form, setForm] = useState(null);
  const [errors, setErrors] = useState({});
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setForm({ name: user.name, email: user.email, date_of_birth: user.date_of_birth, schedule_key: user.schedule_key,
      reminders_enabled: user.reminders_enabled, reminder_lead_days: user.reminder_lead_days });
  }, [user]);

  if (schedules.loading || !form) return <Spinner />;
  if (schedules.error) return <ErrorNotice error={schedules.error} onRetry={schedules.retry} />;
  const selected = schedules.data.find((s) => s.key === form.schedule_key);
  const dirty = JSON.stringify(form) !== JSON.stringify({ name: user.name, email: user.email, date_of_birth: user.date_of_birth, schedule_key: user.schedule_key, reminders_enabled: user.reminders_enabled, reminder_lead_days: user.reminder_lead_days });
  const set = (k) => (e) => { setForm((f) => ({ ...f, [k]: e.target.value })); setErrors((x) => ({ ...x, [k]: undefined })); };

  async function save(e) {
    e.preventDefault();
    const err = {};
    if (!form.name.trim()) err.name = "Enter your name.";
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]{2,}$/.test(form.email.trim())) err.email = "Enter a valid email address.";
    if (!form.date_of_birth || form.date_of_birth > todayISO()) err.date_of_birth = "Enter a valid date of birth.";
    setErrors(err);
    if (Object.keys(err).length) return;
    setSaving(true);
    try {
      setUser(await api.updateProfile({ ...form, reminder_lead_days: Number(form.reminder_lead_days) }));
      toast.success("Profile saved. Your schedule status and reminders were updated.");
    } catch (ex) {
      if (Object.keys(ex.fieldErrors).length) setErrors(ex.fieldErrors); else toast.error(ex.message);
    } finally { setSaving(false); }
  }

  return (
    <form onSubmit={save} className="space-y-6" noValidate>
      <PageHeader title="Profile" description="Your details decide which doses are expected for your age." />
      <Panel aria-labelledby="personal">
        <PanelHeader id="personal" title="Personal details" />
        <div className="grid gap-5 p-5 md:grid-cols-2">
          <TextField label="Full name" value={form.name} onChange={set("name")} error={errors.name} maxLength={100} autoComplete="name" />
          <TextField label="Email" type="email" value={form.email} onChange={set("email")} error={errors.email} autoComplete="email" hint="Also your sign-in email." />
          <TextField label="Date of birth" type="date" max={todayISO()} value={form.date_of_birth} onChange={set("date_of_birth")} error={errors.date_of_birth}
            hint="Changing this moves every estimated date." />
        </div>
      </Panel>

      <Panel aria-labelledby="sched">
        <PanelHeader id="sched" title="Vaccination schedule" />
        <div className="space-y-4 p-5">
          <SelectField label="Reference schedule" value={form.schedule_key} onChange={set("schedule_key")} error={errors.schedule_key}>
            {schedules.data.map((s) => <option key={s.key} value={s.key}>{s.name}</option>)}
          </SelectField>
          {selected && (
            <div className="rounded-control bg-paper p-4 text-sm leading-relaxed">
              <p><span className="font-medium">Country:</span> {selected.country}</p>
              <p><span className="font-medium">Version:</span> {selected.version}</p>
              <p><span className="font-medium">Source:</span> {selected.source}</p>
              {selected.description && <p className="mt-2 text-ink-soft">{selected.description}</p>}
              {selected.source_url && <a href={selected.source_url} target="_blank" rel="noreferrer noopener" className="mt-2 inline-flex items-center gap-1.5 font-medium text-teal-700 hover:underline">View source <ExternalLink className="h-3.5 w-3.5" aria-hidden /></a>}
            </div>
          )}
          <Notice>Pick the schedule that matches the country whose programme you follow. Actual recommendations depend on country, age and medical circumstances.</Notice>
        </div>
      </Panel>

      <Panel aria-labelledby="rem">
        <PanelHeader id="rem" title="Reminders" />
        <div className="grid gap-5 p-5 md:grid-cols-2">
          <Toggle checked={form.reminders_enabled} onChange={(v) => setForm((f) => ({ ...f, reminders_enabled: v }))} label="Show reminders" description="In-app only. VaxTrack doesn't send emails or texts." />
          <SelectField label="Remind me" value={form.reminder_lead_days} onChange={set("reminder_lead_days")} disabled={!form.reminders_enabled}>
            {[3, 7, 14, 30].map((d) => <option key={d} value={d}>{d} days before</option>)}
          </SelectField>
        </div>
      </Panel>

      <div className="flex justify-end gap-2">
        <Button variant="secondary" disabled={!dirty} onClick={() => setForm({ name: user.name, email: user.email, date_of_birth: user.date_of_birth, schedule_key: user.schedule_key, reminders_enabled: user.reminders_enabled, reminder_lead_days: user.reminder_lead_days })}>Discard changes</Button>
        <Button type="submit" loading={saving} disabled={!dirty}>Save changes</Button>
      </div>
    </form>
  );
}
