import { api } from "../services/api.js";

/** Fetches the PDF with the user's token and saves it. Returns true on success. */
export async function downloadReport(toast) {
  try {
    const { blob, filename } = await api.downloadReport();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = filename;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 2000);
    toast.success("Your report was downloaded.");
    return true;
  } catch (err) {
    toast.error(err.message || "The report couldn't be created. Try again.");
    return false;
  }
}
