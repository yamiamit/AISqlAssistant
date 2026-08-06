import { Moon, Sun } from "lucide-react";
import { useTheme } from "../../context/ThemeContext";
import { useConnections } from "../../context/ConnectionContext";

export default function Topbar() {
  const { theme, toggleTheme } = useTheme();
  const { connections, activeConnectionId, setActiveConnectionId } = useConnections();

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-slate-200 bg-white px-4 dark:border-slate-800 dark:bg-slate-900">
      <div className="flex items-center gap-2">
        <span className="text-xs font-medium text-slate-500 dark:text-slate-400">Connected database:</span>
        {connections.length > 0 ? (
          <select
            value={activeConnectionId ?? ""}
            onChange={(e) => setActiveConnectionId(Number(e.target.value))}
            className="rounded-md border border-slate-300 bg-white px-2 py-1 text-sm text-slate-800 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
          >
            {connections.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        ) : (
          <span className="text-xs text-amber-600 dark:text-amber-400">None connected yet</span>
        )}
      </div>

      <button
        onClick={toggleTheme}
        className="rounded-lg p-2 text-slate-500 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
        aria-label="Toggle dark mode"
      >
        {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
      </button>
    </header>
  );
}
