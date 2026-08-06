import { KeyRound, Link2 } from "lucide-react";
import type { SchemaTable as SchemaTableType } from "../../types";
import Card from "../common/Card";

export default function SchemaTable({ table }: { table: SchemaTableType }) {
  return (
    <Card className="overflow-hidden">
      <div className="border-b border-slate-200 bg-slate-50 px-4 py-2.5 dark:border-slate-800 dark:bg-slate-800/50">
        <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">{table.name}</h3>
        <p className="text-xs text-slate-500 dark:text-slate-500">{table.columns.length} columns</p>
      </div>
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="text-xs text-slate-500 dark:text-slate-500">
            <th className="px-4 py-1.5 font-medium">Column</th>
            <th className="px-4 py-1.5 font-medium">Type</th>
            <th className="px-4 py-1.5 font-medium">Nullable</th>
            <th className="px-4 py-1.5 font-medium">Key</th>
          </tr>
        </thead>
        <tbody>
          {table.columns.map((col) => {
            const fk = table.foreign_keys.find((f) => f.column === col.name);
            return (
              <tr key={col.name} className="border-t border-slate-100 dark:border-slate-800">
                <td className="px-4 py-1.5 font-mono text-xs text-slate-800 dark:text-slate-200">{col.name}</td>
                <td className="px-4 py-1.5 text-xs text-slate-500 dark:text-slate-500">{col.type}</td>
                <td className="px-4 py-1.5 text-xs text-slate-500 dark:text-slate-500">{col.nullable ? "yes" : "no"}</td>
                <td className="px-4 py-1.5">
                  {col.is_primary_key && (
                    <span className="inline-flex items-center gap-1 rounded bg-amber-50 px-1.5 py-0.5 text-[11px] font-medium text-amber-700 dark:bg-amber-500/10 dark:text-amber-400">
                      <KeyRound className="h-3 w-3" /> PK
                    </span>
                  )}
                  {fk && (
                    <span className="ml-1 inline-flex items-center gap-1 rounded bg-blue-50 px-1.5 py-0.5 text-[11px] font-medium text-blue-700 dark:bg-blue-500/10 dark:text-blue-400">
                      <Link2 className="h-3 w-3" /> {fk.references_table}.{fk.references_column}
                    </span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </Card>
  );
}
