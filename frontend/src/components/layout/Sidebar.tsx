import { NavLink, useNavigate } from "react-router-dom";
import clsx from "clsx";
import { Database, LogOut, MessageSquarePlus, MessagesSquare, FileUp, Star, TableProperties } from "lucide-react";
import { useAuth } from "../../context/AuthContext";

const navItems = [
  { to: "/app", label: "New Chat", icon: MessageSquarePlus, end: true },
  { to: "/app/history", label: "Chat History", icon: MessagesSquare },
  { to: "/app/saved-queries", label: "Saved Queries", icon: Star },
  { to: "/app/connections", label: "Database Connection", icon: Database },
  { to: "/app/schema", label: "Schema Viewer", icon: TableProperties },
  { to: "/app/upload-pdf", label: "Upload PDF", icon: FileUp },
];

export default function Sidebar() {
  const { logout, user } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <aside className="flex h-full w-64 shrink-0 flex-col border-r border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900">
      <div className="flex items-center gap-2 border-b border-slate-200 px-4 py-4 dark:border-slate-800">
        <div className="rounded-lg bg-indigo-600 p-1.5 text-white">
          <Database className="h-4 w-4" />
        </div>
        <span className="text-sm font-semibold text-slate-900 dark:text-slate-100">AI SQL Assistant</span>
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto p-3">
        {navItems.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              clsx(
                "flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-indigo-50 text-indigo-700 dark:bg-indigo-500/10 dark:text-indigo-300"
                  : "text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
              )
            }
          >
            <Icon className="h-4 w-4" />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-slate-200 p-3 dark:border-slate-800">
        <div className="mb-2 truncate px-1 text-xs text-slate-500 dark:text-slate-500">{user?.email}</div>
        <button
          onClick={handleLogout}
          className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800"
        >
          <LogOut className="h-4 w-4" />
          Logout
        </button>
      </div>
    </aside>
  );
}
