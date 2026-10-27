import { Search } from "lucide-react";
import { SelectField } from "./Form.jsx";

export const STATUS_FILTERS = [["", "All statuses"], ["confirmed", "Confirmed"], ["unverified", "Not confirmed"], ["attention", "Needs attention"]];

export function applyFilters(records, f) {
  const q = f.q.trim().toLowerCase();
  return records.filter((r) => {
    if (q && !r.vaccine_name.toLowerCase().includes(q)) return false;
    if (f.vaccine && r.vaccine_name !== f.vaccine) return false;
    if (f.year && String(r.vaccination_date || "").slice(0, 4) !== f.year && !(f.year === "none" && !r.vaccination_date)) return false;
    if (f.status === "confirmed" && r.verification_status !== "confirmed") return false;
    if (f.status === "unverified" && r.verification_status !== "unverified") return false;
    if (f.status === "attention" && !r.needs_attention) return false;
    return true;
  });
}

export default function RecordFilters({ records, filters, onChange }) {
  const vaccines = [...new Set(records.map((r) => r.vaccine_name))].sort();
  const years = [...new Set(records.filter((r) => r.vaccination_date).map((r) => r.vaccination_date.slice(0, 4)))].sort().reverse();
  const hasUndated = records.some((r) => !r.vaccination_date);
  const set = (k) => (e) => onChange({ ...filters, [k]: e.target.value });
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-[1.4fr_1fr_1fr_1fr]">
      <div>
        <label htmlFor="record-search" className="mb-1.5 block text-sm font-medium">Search</label>
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-muted" aria-hidden />
          <input id="record-search" className="field pl-9" placeholder="Vaccine name" value={filters.q} onChange={set("q")} />
        </div>
      </div>
      <SelectField label="Vaccine" value={filters.vaccine} onChange={set("vaccine")}>
        <option value="">All vaccines</option>{vaccines.map((v) => <option key={v}>{v}</option>)}
      </SelectField>
      <SelectField label="Year" value={filters.year} onChange={set("year")}>
        <option value="">All years</option>{years.map((y) => <option key={y}>{y}</option>)}
        {hasUndated && <option value="none">Date not recorded</option>}
      </SelectField>
      <SelectField label="Status" value={filters.status} onChange={set("status")}>
        {STATUS_FILTERS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
      </SelectField>
    </div>
  );
}
