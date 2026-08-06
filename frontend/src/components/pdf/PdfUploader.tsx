import { useState } from "react";
import { FileUp, Upload } from "lucide-react";
import type { SchemaTable } from "../../types";
import Button from "../common/Button";

interface PdfUploaderProps {
  tables: SchemaTable[];
  onUpload: (file: File, targetTable: string) => void;
  isUploading: boolean;
}

export default function PdfUploader({ tables, onUpload, isUploading }: PdfUploaderProps) {
  const [file, setFile] = useState<File | null>(null);
  const [targetTable, setTargetTable] = useState(tables[0]?.name ?? "");

  return (
    <div className="flex flex-col gap-4 rounded-xl border border-dashed border-slate-300 bg-white p-6 dark:border-slate-700 dark:bg-slate-900">
      <div>
        <label className="mb-1 block text-sm font-medium text-slate-700 dark:text-slate-300">Target table</label>
        <select
          value={targetTable}
          onChange={(e) => setTargetTable(e.target.value)}
          className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
        >
          {tables.map((t) => (
            <option key={t.name} value={t.name}>
              {t.name}
            </option>
          ))}
        </select>
      </div>

      <label className="flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed border-slate-300 py-10 text-center hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800/50">
        <FileUp className="h-8 w-8 text-slate-400" />
        <span className="text-sm text-slate-600 dark:text-slate-400">
          {file ? file.name : "Click to choose a PDF (invoice, product list, sales report...)"}
        </span>
        <input
          type="file"
          accept="application/pdf"
          className="hidden"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />
      </label>

      <Button
        onClick={() => file && onUpload(file, targetTable)}
        disabled={!file || !targetTable}
        isLoading={isUploading}
        className="self-start"
      >
        <Upload className="h-4 w-4" /> Extract Data
      </Button>
    </div>
  );
}
