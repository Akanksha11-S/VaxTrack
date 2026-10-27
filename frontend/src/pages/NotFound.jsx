import { Link } from "react-router-dom";
import Logo from "../components/Logo.jsx";

export default function NotFound() {
  return (
    <div className="mx-auto flex min-h-screen max-w-md flex-col items-start justify-center gap-4 px-6">
      <Logo />
      <h1 className="page-title">That page doesn't exist</h1>
      <p className="text-ink-muted">The link may be out of date. Head back to your dashboard or the home page.</p>
      <div className="flex gap-4 text-sm font-medium text-teal-700">
        <Link to="/app" className="hover:underline">Open dashboard</Link>
        <Link to="/" className="hover:underline">Go to home</Link>
      </div>
    </div>
  );
}
