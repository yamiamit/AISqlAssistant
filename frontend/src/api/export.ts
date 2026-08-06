import { apiClient } from "./client";

async function downloadBlob(url: string, filename: string) {
  const response = await apiClient.get(url, { responseType: "blob" });
  const blobUrl = window.URL.createObjectURL(response.data as Blob);
  const link = document.createElement("a");
  link.href = blobUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(blobUrl);
}

export function exportCsv(messageId: number) {
  return downloadBlob(`/api/export/csv/${messageId}`, `query_results_${messageId}.csv`);
}

export function exportPdfReport(messageId: number) {
  return downloadBlob(`/api/export/pdf-report/${messageId}`, `query_report_${messageId}.pdf`);
}
