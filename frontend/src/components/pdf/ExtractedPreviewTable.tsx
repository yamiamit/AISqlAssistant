import { Trash2 } from "lucide-react";

interface ExtractedPreviewTableProps {
  columns: string[];
  records: Record<string, unknown>[];
  onChange: (records: Record<string, unknown>[]) => void;
}

export default function ExtractedPreviewTable({ columns, records, onChange }: ExtractedPreviewTableProps) {
  function updateCell(rowIndex: number, column: string, value: string) {
    const next = records.map((r, i) => (i === rowIndex ? { ...r, [column]: value } : r));
    onChange(next);
  }

  function removeRow(rowIndex: number) {
    onChange(records.filter((_, i) => i !== rowIndex));
  }

  return (
    <div className="max-h-96 overflow-auto rounded-lg border border-slate-200 dark:border-slate-800">
      <table className="w-full text-left text-sm">
        <thead className="sticky top-0 bg-slate-100 dark:bg-slate-800">
          <tr>
            {columns.map((col) => (
              <th key={col} className="whitespace-nowrap px-2 py-2 text-xs font-medium text-slate-700 dark:text-slate-300">
                {col}
              </th>
            ))}
            <th className="w-10" />
          </tr>
        </thead>
        <tbody>
          {records.map((record, rowIndex) => (
            <tr key={rowIndex} className="border-t border-slate-100 dark:border-slate-800">
              {columns.map((col) => (
                <td key={col} className="px-1 py-1">
                  <input
                    value={record[col] == null ? "" : String(record[col])}
                    onChange={(e) => updateCell(rowIndex, col, e.target.value)}
                    className="w-full min-w-24 rounded border border-transparent bg-transparent px-2 py-1 text-xs text-slate-800 focus:border-indigo-400 focus:bg-white focus:outline-none dark:text-slate-200 dark:focus:bg-slate-800"
                  />
                </td>
              ))}
              <td>
                <button
                  onClick={() => removeRow(rowIndex)}
                  className="rounded p-1.5 text-slate-400 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-950/50"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
