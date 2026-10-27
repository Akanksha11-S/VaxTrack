import { useEffect, useState } from "react";
import { ExternalLink, Search, Sparkles } from "lucide-react";
import PageHeader from "../components/PageHeader.jsx";
import { Panel, PanelHeader } from "../components/Panel.jsx";
import Button from "../components/Button.jsx";
import { Badge } from "../components/Badge.jsx";
import { TextArea } from "../components/Form.jsx";
import { EmptyState, ErrorNotice, Notice, Spinner } from "../components/Feedback.jsx";
import { useAsync } from "../hooks/useAsync.js";
import { api } from "../services/api.js";

const EXAMPLE = "The MMR vaccine provides protection against measles, mumps, and rubella.";
const METHOD = {
  llm: ["blue", "Written by an AI assistant from the text you supplied"],
  rules: ["neutral", "Simplified with built-in rules"],
  curated: ["green", "Curated explanation from the vaccine library"],
};

function Explainer({ status }) {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [out, setOut] = useState(null);
  const [err, setErr] = useState("");

  async function run() {
    setErr(""); setOut(null);
    if (text.trim().length < 10) { setErr("Paste at least a sentence of text to simplify."); return; }
    setBusy(true);
    try { setOut(await api.explain({ text })); } catch (e) { setErr(e.message); } finally { setBusy(false); }
  }

  return (
    <Panel aria-labelledby="explain">
      <PanelHeader id="explain" title="Explain it simply" description="Paste a technical description of a vaccine and get a plain-language version." />
      <div className="space-y-4 p-5">
        <TextArea label="Technical text" value={text} onChange={(e) => setText(e.target.value)} maxLength={1500} rows={4}
          placeholder="For example: Pentavalent vaccine provides protection against diphtheria, tetanus, pertussis, hepatitis B and Haemophilus influenzae type b." />
        <div className="flex flex-wrap items-center gap-3">
          <Button icon={Sparkles} loading={busy} onClick={run}>Simplify</Button>
          <Button variant="quiet" onClick={() => setText(EXAMPLE)} className="text-sm">Use an example</Button>
        </div>
        {err && <p className="text-sm font-medium text-rose-700" role="alert">{err}</p>}
        {out && (
          <div className="rounded-panel border border-teal-100 bg-teal-50 p-4" aria-live="polite">
            <p className="leading-relaxed">{out.text}</p>
            <div className="mt-3 flex flex-wrap items-center gap-2"><Badge tone={METHOD[out.method][0]}>{METHOD[out.method][1]}</Badge></div>
            <p className="mt-2 text-xs text-ink-muted">{out.notice}</p>
          </div>
        )}
        <p className="text-xs leading-relaxed text-ink-muted">
          {status?.llm_enabled
            ? `Text you paste here is sent to the configured AI service (${status.provider}) to be rewritten. Your records and uploaded documents are never sent.`
            : "No AI service is configured, so text is simplified on this server using built-in rules. Nothing you paste leaves the app."}
          {" "}The assistant only rewords the text you give it and never adds medical advice.
        </p>
      </div>
    </Panel>
  );
}

function VaccineEntry({ v }) {
  return (
    <details className="group border-b border-line last:border-0">
      <summary className="flex cursor-pointer list-none items-start justify-between gap-3 px-5 py-4 hover:bg-paper [&::-webkit-details-marker]:hidden">
        <div className="min-w-0">
          <p className="font-medium">{v.name}</p>
          <p className="mt-0.5 text-sm text-ink-muted">{v.diseases.join(", ")}</p>
        </div>
        <Badge tone="blue" className="mt-0.5 hidden sm:inline-flex">{v.category}</Badge>
      </summary>
      <div className="grid gap-5 px-5 pb-6 pt-1 text-sm leading-relaxed md:grid-cols-2">
        <div className="space-y-4">
          <div><h3 className="font-semibold">In simple words</h3><p className="mt-1 rounded-control bg-teal-50 p-3 text-ink-soft">{v.simple_explanation}</p></div>
          <div><h3 className="font-semibold">What it's for</h3><p className="mt-1 text-ink-soft">{v.purpose}</p></div>
          <div><h3 className="font-semibold">Helps protect against</h3>
            <ul className="mt-1 list-disc space-y-0.5 pl-5 text-ink-soft">{v.diseases.map((d) => <li key={d}>{d}</li>)}</ul></div>
        </div>
        <div className="space-y-4">
          <div><h3 className="font-semibold">Doses</h3><p className="mt-1 text-ink-soft">{v.doses_info}</p></div>
          <div><h3 className="font-semibold">Good to know</h3>
            <ul className="mt-1 list-disc space-y-0.5 pl-5 text-ink-soft">{v.educational_notes.map((n) => <li key={n}>{n}</li>)}</ul></div>
          <div><h3 className="font-semibold">Technical description</h3><p className="mt-1 text-ink-muted">{v.technical_description}</p></div>
          <div><h3 className="font-semibold">Sources</h3>
            <ul className="mt-1 space-y-1">{v.sources.map((s) => (
              <li key={s.url}><a href={s.url} target="_blank" rel="noreferrer noopener" className="inline-flex items-center gap-1.5 text-teal-700 hover:underline">{s.name}<ExternalLink className="h-3.5 w-3.5" aria-hidden /></a></li>
            ))}</ul></div>
        </div>
      </div>
    </details>
  );
}

export default function Vaccines() {
  const [q, setQ] = useState("");
  const [debounced, setDebounced] = useState("");
  const [category, setCategory] = useState("");
  useEffect(() => { const t = setTimeout(() => setDebounced(q), 200); return () => clearTimeout(t); }, [q]);
  const { data, loading, error, retry } = useAsync(() => api.vaccines({ q: debounced, category }), [debounced, category]);
  const status = useAsync(() => api.assistantStatus(), []);

  return (
    <div className="space-y-6">
      <PageHeader title="Vaccine information" description="What common vaccines are for, in plain language, with links to the public-health sources behind them." />
      <Explainer status={status.data} />

      <div className="flex flex-wrap items-end gap-3">
        <div className="min-w-[14rem] flex-1">
          <label htmlFor="vsearch" className="mb-1.5 block text-sm font-medium">Search vaccines</label>
          <div className="relative"><Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-muted" aria-hidden />
            <input id="vsearch" className="field pl-9" placeholder="A vaccine or a disease, for example polio" value={q} onChange={(e) => setQ(e.target.value)} /></div>
        </div>
        <div className="flex flex-wrap gap-2" role="group" aria-label="Category">
          {["", ...(data?.categories || [])].map((c) => (
            <button key={c || "all"} aria-pressed={category === c} onClick={() => setCategory(c)}
              className={`rounded-full border px-3.5 py-2 text-sm font-medium ${category === c ? "border-teal-600 bg-teal-600 text-white" : "border-line-strong bg-white text-ink-soft hover:bg-paper"}`}>{c || "All"}</button>
          ))}
        </div>
      </div>

      {error ? <ErrorNotice error={error} onRetry={retry} /> : loading && !data ? <Spinner /> : (
        <Panel className="overflow-hidden" aria-label="Vaccine library">
          {data.vaccines.length ? data.vaccines.map((v) => <VaccineEntry key={v.id} v={v} />)
            : <EmptyState icon={Search} title="No vaccines match your search">Try a different name, or search by disease.</EmptyState>}
        </Panel>
      )}
      {data && <Notice>{data.notice} Library version {data.library_version}. Dose information is general; your national schedule may differ.</Notice>}
    </div>
  );
}
