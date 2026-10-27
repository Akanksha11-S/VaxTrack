import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AlertTriangle, FileText, ImageIcon, Plus, ScanLine, Trash2, UploadCloud, X } from "lucide-react";
import PageHeader from "../components/PageHeader.jsx";
import { Panel, PanelHeader } from "../components/Panel.jsx";
import Button from "../components/Button.jsx";
import { Badge } from "../components/Badge.jsx";
import { ConfirmDialog, Modal } from "../components/Modal.jsx";
import { EmptyState, ErrorNotice, Notice, Spinner } from "../components/Feedback.jsx";
import VaccineNameList, { VACCINE_LIST_ID } from "../components/VaccineNameList.jsx";
import { DOSE_OPTIONS } from "../components/RecordFormModal.jsx";
import { useAsync } from "../hooks/useAsync.js";
import { useToast } from "../hooks/useToast.jsx";
import { api } from "../services/api.js";
import { formatDate, todayISO } from "../utils/format.js";

const MAX_MB = 10;
const ALLOWED = { jpg: "image", jpeg: "image", png: "image", pdf: "pdf" };

function checkFile(file) {
  const ext = file.name.split(".").pop().toLowerCase();
  if (!ALLOWED[ext]) return "That file type isn't supported. Choose a JPG, PNG or PDF.";
  if (file.size === 0) return "This file is empty. Choose another one.";
  if (file.size > MAX_MB * 1024 * 1024) return `This file is larger than ${MAX_MB} MB. Choose a smaller file or a lower-resolution scan.`;
  return null;
}
const sizeText = (b) => (b > 1048576 ? `${(b / 1048576).toFixed(1)} MB` : `${Math.max(1, Math.round(b / 1024))} KB`);

let rowCounter = 0;
const newRow = (over = {}) => ({
  key: `row-${++rowCounter}`, vaccine_name: "", dose_number: "", vaccination_date: "", next_due_date: "", next_due_date_estimated: false, notes: "", verified: false,
  source: "manual", ocr_confidence: null, issues: [], raw_line: null, ...over,
});

function Dropzone({ onPick, error }) {
  const [over, setOver] = useState(false);
  const input = useRef(null);
  const handle = (files) => files?.[0] && onPick(files[0]);
  return (
    <div>
      <div onDragOver={(e) => { e.preventDefault(); setOver(true); }} onDragLeave={() => setOver(false)}
        onDrop={(e) => { e.preventDefault(); setOver(false); handle(e.dataTransfer.files); }}
        className={`flex flex-col items-center gap-3 rounded-panel border-2 border-dashed px-6 py-12 text-center transition-colors ${over ? "border-teal-600 bg-teal-50" : "border-line-strong bg-white"}`}>
        <UploadCloud className="h-9 w-9 text-teal-600" aria-hidden />
        <div>
          <p className="font-medium">Drag a vaccination card here</p>
          <p className="mt-1 text-sm text-ink-muted">JPG, PNG or PDF, up to {MAX_MB} MB. Photos taken in good light work best.</p>
        </div>
        <Button variant="secondary" onClick={() => input.current?.click()}>Choose a file</Button>
        <input ref={input} type="file" className="sr-only" accept=".jpg,.jpeg,.png,.pdf,image/jpeg,image/png,application/pdf"
          aria-label="Choose a vaccination card file" onChange={(e) => { handle(e.target.files); e.target.value = ""; }} />
      </div>
      {error && <p className="mt-3 text-sm font-medium text-rose-700" role="alert">{error}</p>}
    </div>
  );
}

function RowIssues({ row }) {
  if (!row.issues.length && !row.raw_line) return null;
  return (
    <div className="mt-1.5 space-y-1 text-xs">
      {row.issues.map((i) => <p key={i} className="flex items-start gap-1.5 text-amber-700"><AlertTriangle className="mt-px h-3.5 w-3.5 shrink-0" aria-hidden />{i}</p>)}
      {row.raw_line && (
        <details className="text-ink-muted"><summary className="cursor-pointer hover:text-ink">Text read from the card</summary>
          <p className="mt-1 rounded bg-paper px-2 py-1 font-mono">{row.raw_line}</p></details>
      )}
    </div>
  );
}

function ReviewTable({ rows, update, remove, errors }) {
  return (
    <table className="block w-full text-sm md:table">
      <thead className="hidden md:table-header-group">
        <tr className="border-b border-line text-left text-xs text-ink-muted">
          <th className="px-3 py-2.5 font-medium">Source</th><th className="px-3 py-2.5 font-medium">Vaccine</th>
          <th className="px-3 py-2.5 font-medium">Dose</th><th className="px-3 py-2.5 font-medium">Date given</th><th className="px-3 py-2.5 font-medium">Next due date</th>
          <th className="px-3 py-2.5 font-medium">Confirmed</th><th className="px-3 py-2.5"><span className="sr-only">Remove</span></th>
        </tr>
      </thead>
      <tbody className="block md:table-row-group">
        {rows.map((r, idx) => {
          const e = errors[r.key] || {};
          const cell = "block px-3 py-1.5 md:table-cell md:align-top md:py-3 before:mb-1 before:block before:text-xs before:text-ink-muted before:content-[attr(data-label)] md:before:hidden";
          return (
            <tr key={r.key} className={`block border-b border-line px-1 py-3 md:table-row md:p-0 ${e.vaccine_name || e.vaccination_date ? "bg-rose-50/50" : ""}`}>
              <td data-label="Source" className={cell}>
                {r.source === "ocr" ? <Badge tone="blue">Read from card</Badge> : <Badge>Added by you</Badge>}
                {r.ocr_confidence !== null && r.source === "ocr" && <p className="mt-1 text-xs text-ink-muted">{Math.round(r.ocr_confidence)}% legibility</p>}
              </td>
              <td data-label="Vaccine" className={`${cell} md:min-w-[15rem]`}>
                <input className="field" list={VACCINE_LIST_ID} value={r.vaccine_name} aria-label={`Vaccine name, row ${idx + 1}`} maxLength={100}
                  aria-invalid={e.vaccine_name ? "true" : undefined} placeholder="Choose or type a vaccine"
                  onChange={(ev) => update(r.key, { vaccine_name: ev.target.value })} />
                {e.vaccine_name && <p className="mt-1 text-xs font-medium text-rose-700">{e.vaccine_name}</p>}
                <RowIssues row={r} />
              </td>
              <td data-label="Dose" className={`${cell} md:w-36`}>
                <select className="field" value={r.dose_number} aria-label={`Dose, row ${idx + 1}`} onChange={(ev) => update(r.key, { dose_number: ev.target.value })}>
                  {DOSE_OPTIONS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </select>
              </td>
              <td data-label="Date given" className={`${cell} md:w-44`}>
                <input type="date" className="field" max={todayISO()} value={r.vaccination_date} aria-label={`Date given, row ${idx + 1}`}
                  aria-invalid={e.vaccination_date ? "true" : undefined} onChange={(ev) => update(r.key, { vaccination_date: ev.target.value })} />
                {e.vaccination_date && <p className="mt-1 text-xs font-medium text-rose-700">{e.vaccination_date}</p>}
                {!r.vaccination_date && !e.vaccination_date && <p className="mt-1 text-xs text-ink-muted">Left blank: date not recorded</p>}
              </td>
              <td data-label="Next due date" className={`${cell} md:w-44`}>
                <input type="date" className="field" min={r.vaccination_date || undefined} value={r.next_due_date || ""} aria-label={`Next due date, row ${idx + 1}`}
                  onChange={(ev) => update(r.key, { next_due_date: ev.target.value, next_due_date_estimated: false })} />
                <p className="mt-1 text-xs text-ink-muted">Leave blank to use a tentative schedule estimate.</p>
              </td>
              <td data-label="Confirmed" className={cell}>
                <label className="flex cursor-pointer items-center gap-2 py-2">
                  <input type="checkbox" className="h-4 w-4 accent-teal-600" checked={r.verified} onChange={(ev) => update(r.key, { verified: ev.target.checked })} />
                  <span className={r.verified ? "font-medium text-sage-700" : "text-ink-muted"}>{r.verified ? "Confirmed by you" : "Not confirmed"}</span>
                </label>
              </td>
              <td className={`${cell} md:w-12 md:text-right`}>
                <button onClick={() => remove(r.key)} className="rounded p-2 text-ink-muted hover:bg-rose-50 hover:text-rose-700" aria-label={`Remove row ${idx + 1}`}><Trash2 className="h-4 w-4" /></button>
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

export default function Upload() {
  const navigate = useNavigate();
  const toast = useToast();
  const [file, setFile] = useState(null);
  const [fileError, setFileError] = useState("");
  const [stage, setStage] = useState("select"); // select | working | review
  const [step, setStep] = useState("");
  const [fail, setFail] = useState(null);
  const [doc, setDoc] = useState(null);
  const [result, setResult] = useState(null);
  const [rows, setRows] = useState([]);
  const [errors, setErrors] = useState({});
  const [saving, setSaving] = useState(false);
  const [dupes, setDupes] = useState(null);
  const abort = useRef(null);
  const docs = useAsync(() => api.listDocuments(), []);
  const [toDelete, setToDelete] = useState(null);

  const preview = useMemo(() => (file && ALLOWED[file.name.split(".").pop().toLowerCase()] === "image" ? URL.createObjectURL(file) : null), [file]);
  useEffect(() => () => preview && URL.revokeObjectURL(preview), [preview]);

  function pick(f) {
    const problem = checkFile(f);
    setFileError(problem || ""); setFail(null);
    setFile(problem ? null : f);
  }
  function reset() { setFile(null); setStage("select"); setDoc(null); setResult(null); setRows([]); setErrors({}); setFail(null); setFileError(""); }

  async function readCard() {
    setFail(null); setStage("working"); setStep("Uploading your file");
    abort.current = new AbortController();
    try {
      const uploaded = await api.uploadDocument(file, abort.current.signal);
      setDoc(uploaded); setStep("Reading the card. This can take a few seconds.");
      const out = await api.extractDocument(uploaded.id, abort.current.signal);
      setResult(out);
      setRows(out.records.map((r) => newRow({
        vaccine_name: r.vaccine_name, dose_number: r.dose_number === null ? "" : String(r.dose_number), vaccination_date: r.vaccination_date || "", next_due_date: r.next_due_date || "", next_due_date_estimated: Boolean(r.next_due_date_estimated),
        notes: r.notes || "", source: "ocr", ocr_confidence: r.ocr_confidence, issues: r.issues, raw_line: r.raw_line,
      })));
      setStage("review"); docs.reload();
    } catch (err) {
      if (err.name === "AbortError") { setStage("select"); toast.success("Cancelled. Nothing was saved."); docs.reload(); return; }
      setFail(err); setStage("select"); docs.reload();
    }
  }

  const update = useCallback((key, patch) => {
    setRows((rs) => rs.map((r) => (r.key === key ? { ...r, ...patch } : r)));
    setErrors((e) => ({ ...e, [key]: undefined }));
  }, []);
  const remove = useCallback((key) => setRows((rs) => rs.filter((r) => r.key !== key)), []);

  function validate() {
    const e = {};
    rows.forEach((r) => {
      const x = {};
      if (!r.vaccine_name.trim()) x.vaccine_name = "Choose or type a vaccine name.";
      if (r.vaccination_date && r.vaccination_date > todayISO()) x.vaccination_date = "A vaccination date can't be in the future.";
      if (r.next_due_date && r.vaccination_date && r.next_due_date <= r.vaccination_date) x.next_due_date = "Next due date must be after the date given.";
      if (Object.keys(x).length) e[r.key] = x;
    });
    setErrors(e);
    return Object.keys(e).length === 0;
  }

  async function save(allowDuplicates = false) {
    if (!validate()) { toast.error("Fix the highlighted rows before saving."); return; }
    setSaving(true);
    try {
      const body = {
        document_id: doc?.id ?? null, allow_duplicates: allowDuplicates,
        records: rows.map((r) => ({
          vaccine_name: r.vaccine_name.trim(), dose_number: r.dose_number === "" ? null : Number(r.dose_number),
          vaccination_date: r.vaccination_date || null, next_due_date: r.next_due_date || null, next_due_date_estimated: Boolean(r.next_due_date_estimated), notes: r.notes || null,
          verification_status: r.verified ? "confirmed" : "unverified", source_type: r.source, ocr_confidence: r.ocr_confidence,
        })),
      };
      const out = await api.createBulk(body);
      toast.success(`${out.saved} record${out.saved === 1 ? "" : "s"} saved.`);
      navigate("/app/history");
    } catch (err) {
      if (err.code === "possible_duplicate") setDupes(err.data.detail.duplicates);
      else toast.error(err.message);
    } finally { setSaving(false); }
  }

  async function deleteDoc() {
    try { await api.deleteDocument(toDelete.id); toast.success("The uploaded file was deleted."); setToDelete(null); docs.reload(); }
    catch (err) { toast.error(err.message); }
  }

  const confirmed = rows.filter((r) => r.verified).length;
  const ocrMissing = fail?.code === "tesseract_missing";

  return (
    <div className="space-y-6">
      <VaccineNameList />
      <PageHeader title="Upload a vaccination card"
        description="VaxTrack suggests what the card says. Nothing is saved or counted until you've checked it." />

      {stage === "select" && (
        <>
          {fail && (
            <ErrorNotice error={{ message: ocrMissing ? "Reading cards isn't set up on this server yet (Tesseract OCR is missing). Add your records manually for now, or see the README for setup steps." : fail.message }} />
          )}
          {!file ? <Dropzone onPick={pick} error={fileError} /> : (
            <Panel className="p-5">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div className="flex min-w-0 items-center gap-3">
                  {preview ? <img src={preview} alt="Selected card preview" className="h-16 w-16 rounded-control border border-line object-cover" />
                    : <span className="flex h-16 w-16 items-center justify-center rounded-control bg-teal-50 text-teal-700"><FileText className="h-7 w-7" aria-hidden /></span>}
                  <div className="min-w-0"><p className="truncate font-medium">{file.name}</p><p className="text-sm text-ink-muted">{sizeText(file.size)} - ready to read</p></div>
                </div>
                <div className="flex gap-2">
                  <Button variant="secondary" icon={X} onClick={reset}>Remove</Button>
                  <Button icon={ScanLine} onClick={readCard}>Read card</Button>
                </div>
              </div>
            </Panel>
          )}
          <p className="text-sm text-ink-muted">
            Prefer to type? <button className="font-medium text-teal-700 hover:underline" onClick={() => { setRows([newRow({ verified: true })]); setResult({ warnings: [] }); setStage("review"); }}>Add records manually</button>
          </p>
        </>
      )}

      {stage === "working" && (
        <Panel className="p-8">
          <Spinner label={step} className="!py-4" />
          <ol className="mx-auto mt-2 max-w-xs space-y-1.5 text-sm text-ink-muted" aria-label="Progress">
            <li className={step.startsWith("Uploading") ? "font-medium text-ink" : ""}>Upload the file</li>
            <li className={step.startsWith("Reading") ? "font-medium text-ink" : ""}>Clean up the image and read the text</li>
            <li>Match vaccine names, dates and doses</li>
          </ol>
          <div className="mt-5 text-center"><Button variant="secondary" onClick={() => abort.current?.abort()}>Cancel</Button></div>
        </Panel>
      )}

      {stage === "review" && (
        <div className="grid gap-6 xl:grid-cols-[16rem_1fr]">
          {(preview || file) && (
            <aside className="xl:sticky xl:top-6 xl:self-start">
              <Panel className="p-3">
                {preview ? <img src={preview} alt="The card you uploaded" className="max-h-72 w-full rounded-control object-contain xl:max-h-[28rem]" />
                  : <div className="flex items-center gap-3 p-2 text-sm"><ImageIcon className="h-5 w-5 text-ink-muted" aria-hidden /><span className="truncate">{file?.name}</span></div>}
                <p className="mt-2 px-1 text-xs text-ink-muted">Compare each row with your card.</p>
              </Panel>
            </aside>
          )}
          <Panel aria-labelledby="review">
            <PanelHeader id="review" title="Check what was read"
              description={rows.length ? `${rows.length} suggestion${rows.length === 1 ? "" : "s"}. Edit anything that's wrong, then confirm the rows you trust.` : undefined}
              action={<div className="flex gap-2">
                <Button variant="secondary" size="sm" icon={Plus} onClick={() => setRows((r) => [...r, newRow({ verified: true })])}>Add a row</Button>
                {rows.length > 0 && <Button variant="secondary" size="sm" onClick={() => setRows((rs) => rs.map((r) => ({ ...r, verified: confirmed !== rs.length })))}>{confirmed === rows.length ? "Unconfirm all" : "Confirm all"}</Button>}
              </div>} />
            {result?.warnings?.map((w) => <div key={w} className="px-5 pt-4"><Notice tone="warn">{w}</Notice></div>)}
            {result?.average_confidence != null && result.average_confidence < 70 && (
              <div className="px-5 pt-4"><Notice tone="warn">The scan was hard to read (average legibility {Math.round(result.average_confidence)}%). Check every field carefully, or try a sharper photo.</Notice></div>
            )}
            {rows.length ? <div className="p-2 md:p-3"><ReviewTable rows={rows} update={update} remove={remove} errors={errors} /></div>
              : <EmptyState icon={ScanLine} title="No vaccinations were found" action={<Button size="sm" icon={Plus} onClick={() => setRows([newRow({ verified: true })])}>Add a row</Button>}>
                You can add the vaccinations by hand, or go back and try a clearer file.</EmptyState>}
            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line px-5 py-4">
              <p className="text-sm text-ink-muted">{rows.length ? `${confirmed} confirmed, ${rows.length - confirmed} not confirmed. Not-confirmed rows are saved but never counted as completed.` : "Nothing to save yet."}</p>
              <div className="flex gap-2">
                <Button variant="secondary" onClick={reset}>Start over</Button>
                <Button loading={saving} disabled={!rows.length} onClick={() => save(false)}>Save {rows.length || ""} record{rows.length === 1 ? "" : "s"}</Button>
              </div>
            </div>
          </Panel>
        </div>
      )}

      <Panel aria-labelledby="uploads">
        <PanelHeader id="uploads" title="Your uploaded files" description="Files are deleted automatically after 30 days. Records you saved from them stay." />
        {docs.loading ? <Spinner className="!py-6" /> : docs.data?.length ? (
          <ul className="row-divide">
            {docs.data.map((d) => (
              <li key={d.id} className="flex items-center justify-between gap-3 px-5 py-3">
                <div className="min-w-0"><p className="truncate text-sm font-medium">{d.original_filename}</p>
                  <p className="text-xs text-ink-muted">{formatDate(d.uploaded_at)} - {sizeText(d.size_bytes)} - {d.processing_status.replace("_", " ")}</p></div>
                <Button variant="ghost" size="sm" icon={Trash2} onClick={() => setToDelete(d)} disabled={!d.file_available && false}>Delete file</Button>
              </li>
            ))}
          </ul>
        ) : <p className="px-5 py-5 text-sm text-ink-muted">No files uploaded yet.</p>}
      </Panel>

      <ConfirmDialog open={Boolean(toDelete)} title="Delete this file?" confirmLabel="Delete file" onClose={() => setToDelete(null)} onConfirm={deleteDoc}>
        <p>{toDelete?.original_filename} will be removed from the server. Records you saved from it keep their details.</p>
      </ConfirmDialog>

      <Modal open={Boolean(dupes)} onClose={() => setDupes(null)} title="Some rows look like existing records"
        footer={<><Button variant="secondary" onClick={() => setDupes(null)}>Go back and edit</Button>
          <Button loading={saving} onClick={() => { setDupes(null); save(true); }}>Save anyway</Button></>}>
        <ul className="space-y-3 text-sm">
          {dupes?.map((d) => (
            <li key={d.index}><p className="font-medium">Row {d.index + 1}: {rows[d.index]?.vaccine_name}</p>
              <p className="text-ink-muted">Matches {d.matches.map((m) => `${m.vaccine_name}${m.dose_number !== null ? `, dose ${m.dose_number}` : ""} (${formatDate(m.vaccination_date)})`).join("; ")}</p></li>
          ))}
        </ul>
      </Modal>
    </div>
  );
}
