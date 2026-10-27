import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import AuthShell from "../components/AuthShell.jsx";
import Button from "../components/Button.jsx";
import { TextField } from "../components/Form.jsx";
import { Notice } from "../components/Feedback.jsx";
import { useAuth } from "../hooks/useAuth.jsx";

export default function Login() {
  const { login, sessionExpired } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setError("");
    if (!form.email.trim() || !form.password) { setError("Enter your email and password."); return; }
    setBusy(true);
    try {
      await login({ email: form.email, password: form.password });
      navigate(location.state?.from || "/app", { replace: true });
    } catch (err) { setError(err.message); } finally { setBusy(false); }
  }

  return (
    <AuthShell title="Welcome back" subtitle="Sign in to see your vaccination record."
      footer={<>New to VaxTrack? <Link to="/register" className="font-medium text-teal-700 hover:underline">Create an account</Link></>}>
      <form onSubmit={submit} className="space-y-4" noValidate>
        {sessionExpired && <Notice tone="warn">Your session ended. Sign in again to continue.</Notice>}
        <TextField label="Email" type="email" autoComplete="email" value={form.email} data-autofocus
          onChange={(e) => setForm({ ...form, email: e.target.value })} />
        <TextField label="Password" type="password" autoComplete="current-password" value={form.password}
          onChange={(e) => setForm({ ...form, password: e.target.value })} />
        {error && <p className="text-sm font-medium text-rose-700" role="alert">{error}</p>}
        <Button type="submit" loading={busy} className="w-full" size="lg">Sign in</Button>
      </form>
    </AuthShell>
  );
}
