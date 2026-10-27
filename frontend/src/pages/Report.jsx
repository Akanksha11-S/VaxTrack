import { useState } from "react";
import { FileDown } from "lucide-react";
import PageHeader from "../components/PageHeader.jsx";
import { Panel } from "../components/Panel.jsx";
import Button from "../components/Button.jsx";
import { ErrorNotice, Notice, Spinner } from "../components/Feedback.jsx";
import { useAsync } from "../hooks/useAsync.js";
import { useToast } from "../hooks/useToast.jsx";
import { api } from "../services/api.js";
import { downloadReport } from "../utils/download.js";

const INCLUDED = [
  "Your name, date of birth and the report date",
  "The reference schedule, with its version and source",
  "Every saved vaccination with its dose, date and whether it is confirmed",
  "Estimated upcoming doses",
  "Records that need review, and why",
  "A short educational disclaimer",
];

export default function Report() {
  const toast = useToast();
  const { data, loading, error, retry } = useAsync(() => api.dashboard(), []);
  const [busy, setBusy] = useState(false);

  async function get() { setBusy(true); await downloadReport(toast); setBusy(false); }
  if (loading) return <Spinner />;
  if (error) return <ErrorNotice error={error} onRetry={retry} />;
  const { cards } = data;

  return (
    <div className="space-y-6">
      <PageHeader title="PDF report" description="A tidy summary you can keep or show to a healthcare provider. It always uses your latest saved records." />
      <Panel className="grid gap-8 p-6 md:grid-cols-[1.2fr_1fr]">
        <div>
          <h2 className="font-serif text-lg font-semibold">What's in the report</h2>
          <ul className="mt-3 list-disc space-y-1.5 pl-5 text-sm leading-relaxed text-ink-soft">{INCLUDED.map((i) => <li key={i}>{i}</li>)}</ul>
        </div>
        <div className="flex flex-col justify-between gap-5 rounded-control bg-paper p-5">
          <dl className="space-y-2 text-sm">
            <div className="flex justify-between"><dt className="text-ink-muted">Records included</dt><dd className="font-semibold">{cards.total_doses}</dd></div>
            <div className="flex justify-between"><dt className="text-ink-muted">Confirmed</dt><dd className="font-semibold">{cards.confirmed_doses}</dd></div>
            <div className="flex justify-between"><dt className="text-ink-muted">Need review</dt><dd className="font-semibold">{cards.needs_verification}</dd></div>
            <div className="flex justify-between"><dt className="text-ink-muted">Upcoming estimates</dt><dd className="font-semibold">{cards.upcoming_doses}</dd></div>
          </dl>
          <Button icon={FileDown} size="lg" loading={busy} onClick={get} className="w-full">Download PDF report</Button>
        </div>
      </Panel>
      <Notice>This report is for personal record keeping. It is not medical advice and not an official vaccination certificate. Records that aren't confirmed are labelled as such.</Notice>
    </div>
  );
}
