import { useEffect, useState } from "react";
import { api } from "../services/api.js";

export const VACCINE_LIST_ID = "vaxtrack-vaccine-names";
let cache = null;

/** Renders a <datalist> of library vaccine names, fetched once per page load. */
export default function VaccineNameList() {
  const [names, setNames] = useState(cache || []);
  useEffect(() => {
    if (cache) return;
    api.vaccines().then((r) => { cache = r.vaccines.map((v) => v.name); setNames(cache); }).catch(() => {});
  }, []);
  return <datalist id={VACCINE_LIST_ID}>{names.map((n) => <option key={n} value={n} />)}</datalist>;
}
