import { useEffect, useState } from "react";
import { CheckCircle2, Database, FileUp, X } from "lucide-react";
import { useConnections } from "../context/ConnectionContext";
import * as connectionsApi from "../api/connections";
import * as pdfApi from "../api/pdf";
import type { PdfConfirmResult, PdfPreview } from "../api/pdf";
import PdfUploader from "../components/pdf/PdfUploader";
import ExtractedPreviewTable from "../components/pdf/ExtractedPreviewTable";
import Button from "../components/common/Button";
import ErrorBanner from "../components/common/ErrorBanner";
import EmptyState from "../components/common/EmptyState";
import Spinner from "../components/common/Spinner";
import type { SchemaTable } from "../types";

export default function PdfUploadPage() {
  const { activeConnectionId, connections } = useConnections();
  const [tables, setTables] = useState<SchemaTable[]>([]);
  const [isLoadingSchema, setIsLoadingSchema] = useState(false);

  const [isUploading, setIsUploading] = useState(false);
  const [preview, setPreview] = useState<PdfPreview | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [isConfirming, setIsConfirming] = useState(false);
  const [result, setResult] = useState<PdfConfirmResult | null>(null);

  useEffect(() => {
    if (!activeConnectionId) return;
    setIsLoadingSchema(true);
    connectionsApi
      .getSchema(activeConnectionId)
      .then((schema) => setTables(schema.tables))
      .finally(() => setIsLoadingSchema(false));
  }, [activeConnectionId]);

  async function handleUpload(file: File, targetTable: string) {
    if (!activeConnectionId) return;
    setError(null);
    setResult(null);
    setIsUploading(true);
    try {
      const data = await pdfApi.uploadPdf(file, activeConnectionId, targetTable);
      setPreview(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not process this PDF.");
    } finally {
      setIsUploading(false);
    }
  }

  async function handleConfirm() {
    if (!activeConnectionId || !preview) return;
    setIsConfirming(true);
    setError(null);
    try {
      const res = await pdfApi.confirmPdfInsert(activeConnectionId, preview.target_table, preview.records);
      setResult(res);
      setPreview(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not insert these records.");
    } finally {
      setIsConfirming(false);
    }
  }

  function handleCancel() {
    setPreview(null);
    setError(null);
  }

  if (connections.length === 0) {
    return (
      <EmptyState
        icon={<Database className="h-8 w-8" />}
        title="Connect a database first"
        description="Upload PDFs directly into a table on your connected PostgreSQL database."
      />
    );
  }

  return (
    <div className="mx-auto max-w-3xl p-6">
      <h1 className="mb-1 text-lg font-semibold text-slate-900 dark:text-slate-100">Upload PDF</h1>
      <p className="mb-4 text-sm text-slate-500 dark:text-slate-400">
        Upload an invoice, product list, customer list, or sales report — the AI extracts structured records
        for you to review before anything is inserted.
      </p>

      {error && (
        <div className="mb-4">
          <ErrorBanner message={error} />
        </div>
      )}

      {result && (
        <div className="mb-4 flex items-start gap-2 rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700 dark:border-green-900 dark:bg-green-950/50 dark:text-green-300">
          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
          <div>
            <p className="font-medium">
              Inserted {result.inserted_count} row{result.inserted_count === 1 ? "" : "s"}
              {result.skipped_count > 0 ? `, skipped ${result.skipped_count}` : ""}.
            </p>
            {result.warnings.map((w, i) => (
              <p key={i} className="text-xs text-green-700/80 dark:text-green-400/80">
                {w}
              </p>
            ))}
          </div>
        </div>
      )}

      {isLoadingSchema ? (
        <div className="flex justify-center py-16">
          <Spinner />
        </div>
      ) : !preview ? (
        <PdfUploader tables={tables} onUpload={handleUpload} isUploading={isUploading} />
      ) : (
        <div className="flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-slate-700 dark:text-slate-300">
              <FileUp className="mr-1 inline h-4 w-4" />
              {preview.records.length} record{preview.records.length === 1 ? "" : "s"} extracted for{" "}
              <span className="font-mono">{preview.target_table}</span> — review and edit before inserting
            </p>
          </div>

          {preview.warnings.length > 0 && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-700 dark:border-amber-900 dark:bg-amber-950/50 dark:text-amber-300">
              {preview.warnings.map((w, i) => (
                <p key={i}>{w}</p>
              ))}
            </div>
          )}

          <ExtractedPreviewTable
            columns={preview.columns}
            records={preview.records}
            onChange={(records) => setPreview({ ...preview, records })}
          />

          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={handleCancel}>
              <X className="h-4 w-4" /> Cancel
            </Button>
            <Button onClick={handleConfirm} isLoading={isConfirming}>
              Confirm & Insert {preview.records.length} Row{preview.records.length === 1 ? "" : "s"}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
