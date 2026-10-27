import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import AuthShell from "../components/AuthShell.jsx";
import Button from "../components/Button.jsx";
import { SelectField, TextField } from "../components/Form.jsx";
import { useAuth } from "../hooks/useAuth.jsx";
import { api } from "../services/api.js";
import { todayISO } from "../utils/format.js";

// Used only if the schedule list can't be fetched; the real list comes from the API (data/schedules.json).
const FALLBACK = [{ key: "in-uip", name: "India - Universal Immunisation Programme" }, { key: "who-routine", name: "WHO - Routine immunization (global summary)" }];

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: "", email: "", password: "", date_of_birth: "", schedule_key: "in-uip" });
  const [errors, setErrors] = useState({});
  const [busy, setBusy] = useState(false);
  const [schedules, setSchedules] = useState(FALLBACK);
  useEffect(() => { api.scheduleOptions().then((s) => s.length && setSchedules(s)).catch(() => {}); }, []);
  useEffect(() => { document.title = "Create account - VaxTrack"; return () => { document.title = "VaxTrack"; }; }, []);

  const set = (k) => (e) => { setForm((f) => ({ ...f, [k]: e.target.value })); setErrors((x) => ({ ...x, [k]: undefined, form: undefined })); };

  function validate() {
    const e = {};
    if (!form.name.trim()) e.name = "Enter your name.";
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]{2,}$/.test(form.email.trim())) e.email = "Enter a valid email address.";
    if (form.password.length < 8 || !/[A-Za-z]/.test(form.password) || !/\d/.test(form.password)) e.password = "Use at least 8 characters, with a letter and a number.";
    if (!form.date_of_birth) e.date_of_birth = "Enter your date of birth.";
    else if (form.date_of_birth > todayISO()) e.date_of_birth = "Date of birth can't be in the future.";
    setErrors(e);
    return !Object.keys(e).length;
  }

  async function submit(ev) {
    ev.preventDefault();
    if (!validate()) return;
    setBusy(true);
    try {
      await register(form);
      navigate("/app", { replace: true });
    } catch (err) {
      setErrors(Object.keys(err.fieldErrors).length ? err.fieldErrors : { form: err.message });
    } finally { setBusy(false); }
  }

  return (
    <AuthShell title="Create your account" subtitle="Your date of birth is used to work out which doses fit your age."
      footer={<>Already registered? <Link to="/login" className="font-medium text-teal-700 hover:underline">Sign in</Link></>}>
      <form onSubmit={submit} className="space-y-4" noValidate>
        <TextField label="Full name" autoComplete="name" value={form.name} onChange={set("name")} error={errors.name} maxLength={100} data-autofocus />
        <TextField label="Email" type="email" autoComplete="email" value={form.email} onChange={set("email")} error={errors.email}
          hint="You'll use this to sign in." />
        <TextField label="Password" type="password" autoComplete="new-password" value={form.password} onChange={set("password")} error={errors.password}
          hint="At least 8 characters, with a letter and a number." />
        <TextField label="Date of birth" type="date" max={todayISO()} value={form.date_of_birth} onChange={set("date_of_birth")} error={errors.date_of_birth} />
        <SelectField label="Vaccination schedule" value={form.schedule_key} onChange={set("schedule_key")} error={errors.schedule_key}
          hint="The reference your records are compared with. You can change it later.">
          {schedules.map((s) => <option key={s.key} value={s.key}>{s.name}</option>)}
        </SelectField>
        {errors.form && <p className="text-sm font-medium text-rose-700" role="alert">{errors.form}</p>}
        <Button type="submit" loading={busy} className="w-full" size="lg">Create account</Button>
      </form>
    </AuthShell>
  );
}
