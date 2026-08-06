import { useState } from "react";
import { Check, ChevronDown, ChevronUp, Copy } from "lucide-react";

export default function SqlBlock({ sql }: { sql: string }) {
  const [collapsed, setCollapsed] = useState(false);
  const [copied, setCopied] = useState(false);

  function handleCopy() {
    navigator.clipboard.writeText(sql).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  }

  return (
    <div className="overflow-hidden rounded-lg border border-slate-200 dark:border-slate-800">
      <div className="flex items-center justify-between bg-slate-800 px-3 py-1.5">
        <span className="text-xs font-medium text-slate-300">Generated SQL</span>
        <div className="flex items-center gap-1">
          <button
            onClick={handleCopy}
            className="flex items-center gap-1 rounded px-2 py-1 text-xs text-slate-300 hover:bg-slate-700"
          >
            {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
            {copied ? "Copied" : "Copy"}
          </button>
          <button
            onClick={() => setCollapsed((c) => !c)}
            className="flex items-center gap-1 rounded px-2 py-1 text-xs text-slate-300 hover:bg-slate-700"
          >
            {collapsed ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronUp className="h-3.5 w-3.5" />}
            {collapsed ? "Expand" : "Collapse"}
          </button>
        </div>
      </div>
      {!collapsed && (
        <pre className="overflow-x-auto bg-slate-900 px-3 py-2.5 text-xs leading-relaxed text-slate-100">
          <code>{sql}</code>
        </pre>
      )}
    </div>
  );
}
