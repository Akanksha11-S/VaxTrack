import { STATUS } from "../utils/format.js";

// Each pip differs in fill AND outline so status doesn't depend on colour alone.
const PIP = {
  recorded: "bg-sage-500 text-white border-sage-500",
  upcoming: "bg-white text-amber-700 border-amber-500",
  potentially_due: "bg-amber-100 text-amber-700 border-amber-500",
  possibly_missed: "bg-rose-50 text-rose-700 border-rose-500",
  needs_verification: "bg-amber-100 text-amber-700 border-amber-500 border-dashed",
  not_enough_information: "bg-white text-ink-muted border-line-strong border-dashed",
};

export default function DosePips({ doses }) {
  return (
    <ul className="flex flex-wrap gap-1" aria-label="Doses in this schedule">
      {doses.map((d) => (
        <li key={d.dose} title={`${d.dose_label}: ${STATUS[d.status].label}`}
          className={`flex h-6 min-w-[1.5rem] items-center justify-center rounded-md border px-1 text-[11px] font-semibold ${PIP[d.status]}`}>
          {d.dose}
          <span className="sr-only">, {d.dose_label}: {STATUS[d.status].label}</span>
        </li>
      ))}
    </ul>
  );
}
