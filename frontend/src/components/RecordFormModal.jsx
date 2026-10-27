import { useEffect, useState } from "react";
import { AlertTriangle } from "lucide-react";
import { Modal } from "./Modal.jsx";
import Button from "./Button.jsx";
import { SelectField, TextArea, TextField } from "./Form.jsx";
import { api } from "../services/api.js";
import { useToast } from "../hooks/useToast.jsx";
import { formatDate, todayISO } from "../utils/format.js";
import VaccineNameList, { VACCINE_LIST_ID } from "./VaccineNameList.jsx";

export const DOSE_OPTIONS = [["", "Not sure"], ["0", "Dose 0 (birth dose)"], ...Array.from({ length: 10 }, (_, i) => [String(i + 1), `Dose ${i + 1}`])];

const blank = { vaccine_name: "", dose_number: "", vaccination_date: "", notes: "", verification_status: "confirmed" };

export default function RecordFormModal({ open, record, onClose, onSaved }) {
  const toast = useToast();
  const editing = Boolean(record);
  const [form, setForm] = useState(blank);
  const [errors, setErrors] = useState({});
  const [duplicates, setDuplicates] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) return;
    setErrors({}); setDuplicates(null);
    setForm(record ? {
      vaccine_name: record.vaccine_name,
      dose_number: record.dose_number === null ? "" : String(record.dose_number),
      vaccination_date: record.vaccination_date || "",
      notes: record.notes || "",
      verification_status: record.verification_status,
    } : blank);
  }, [open, record]);

  const set = (k) => (e) => { setForm((f) => ({ ...f, [k]: e.target.value })); setErrors((x) => ({ ...x, [k]: undefined })); setDuplicates(null); };

  function validate() {
    const e = {};
    if (!form.vaccine_name.trim()) e.vaccine_name = "Enter or choose a vaccine name.";
    if (form.vaccination_date && form.vaccination_date > todayISO()) e.vaccination_date = "A vaccination date can't be in the future.";
    setErrors(e);
    return Object.keys(e).length === 0;
  }

  async function submit(allowDuplicate = false) {
    if (!validate()) return;
    setSaving(true);
    const body = {
      vaccine_name: form.vaccine_name.trim(),
      dose_number: form.dose_number === "" ? null : Number(form.dose_number),
      vaccination_date: form.vaccination_date || null,
      notes: form.notes.trim() || null,
      verification_status: form.verification_status,
      allow_duplicate: allowDuplicate,
    };
    try {
      const saved = editing ? await api.updateRecord(record.id, body) : await api.createRecord(body);
      toast.success(editing ? "Record updated." : "Record added.");
      onSaved?.(saved);
      onClose();
    } catch (err) {
      if (err.code === "possible_duplicate") setDuplicates(err.data.detail.duplicates[0].matches);
      else if (err.status === 422 && Object.keys(err.fieldErrors).length) setErrors(err.fieldErrors);
      else setErrors({ form: err.message });
    } finally { setSaving(false); }
  }

  return (
    <Modal open={open} onClose={onClose} title={editing ? "Edit vaccination record" : "Add a vaccination"}
      footer={<>
        <Button variant="secondary" onClick={onClose}>Cancel</Button>
        {duplicates
          ? <Button loading={saving} onClick={() => submit(true)}>Save anyway</Button>
          : <Button loading={saving} onClick={() => submit(false)}>{editing ? "Save changes" : "Add record"}</Button>}
      </>}>
      <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); submit(Boolean(duplicates)); }} noValidate>
        <VaccineNameList />
        <TextField label="Vaccine name" list={VACCINE_LIST_ID} value={form.vaccine_name} onChange={set("vaccine_name")}
          error={errors.vaccine_name} placeholder="Start typing, for example Hepatitis B" data-autofocus autoComplete="off" maxLength={100}
          hint="Pick from the list so it can be matched to your schedule. Other names are saved as typed." />
        <div className="grid gap-4 sm:grid-cols-2">
          <SelectField label="Dose" value={form.dose_number} onChange={set("dose_number")} error={errors.dose_number}>
            {DOSE_OPTIONS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </SelectField>
          <TextField label="Date given" type="date" max={todayISO()} value={form.vaccination_date} onChange={set("vaccination_date")}
            error={errors.vaccination_date} optional />
        </div>
        <TextArea label="Notes" value={form.notes} onChange={set("notes")} maxLength={500} optional placeholder="Clinic, batch number, anything worth remembering" error={errors.notes} />
        <fieldset>
          <legend className="mb-1.5 text-sm font-medium">Verification</legend>
          <div className="space-y-2">
            {[["confirmed", "Confirmed", "I checked this against a document, or I'm sure of it."],
              ["unverified", "Not confirmed", "From memory or still to be checked. It won't count as completed."]].map(([v, t, d]) => (
              <label key={v} className={`flex cursor-pointer items-start gap-3 rounded-control border p-3 text-sm ${form.verification_status === v ? "border-teal-600 bg-teal-50" : "border-line"}`}>
                <input type="radio" name="verification" className="mt-1 accent-teal-600" checked={form.verification_status === v}
                  onChange={() => setForm((f) => ({ ...f, verification_status: v }))} />
                <span><span className="font-medium">{t}</span><br /><span className="text-ink-muted">{d}</span></span>
              </label>
            ))}
          </div>
        </fieldset>
        {duplicates && (
          <div className="rounded-panel border border-amber-100 bg-amber-50 p-4 text-sm text-amber-700" role="alert">
            <p className="flex items-center gap-2 font-medium"><AlertTriangle className="h-4 w-4" aria-hidden /> This looks like a record you already have</p>
            <ul className="mt-2 list-disc space-y-0.5 pl-5">
              {duplicates.map((d) => <li key={d.id}>{d.vaccine_name}{d.dose_number !== null && `, dose ${d.dose_number}`} - {formatDate(d.vaccination_date)}</li>)}
            </ul>
            <p className="mt-2">Edit the details above, or choose Save anyway if both are correct.</p>
          </div>
        )}
        {errors.form && <p className="text-sm font-medium text-rose-700" role="alert">{errors.form}</p>}
        <button type="submit" className="hidden" aria-hidden tabIndex={-1} />
      </form>
    </Modal>
  );
}
