import { Database, Pencil, RefreshCw, Trash2 } from "lucide-react";
import type { DBConnection } from "../../types";
import Card from "../common/Card";
import Button from "../common/Button";

interface ConnectionListProps {
  connections: DBConnection[];
  onEdit: (conn: DBConnection) => void;
  onDelete: (conn: DBConnection) => void;
  onRefreshSchema: (conn: DBConnection) => void;
  refreshingId: number | null;
}

export default function ConnectionList({ connections, onEdit, onDelete, onRefreshSchema, refreshingId }: ConnectionListProps) {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
      {connections.map((conn) => (
        <Card key={conn.id} className="p-4">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-2">
              <div className="rounded-lg bg-indigo-50 p-2 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-400">
                <Database className="h-4 w-4" />
              </div>
              <div>
                <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">{conn.name}</p>
                <p className="text-xs text-slate-500 dark:text-slate-500">
                  {conn.username}@{conn.host}:{conn.port}/{conn.database_name}
                </p>
              </div>
            </div>
          </div>

          <p className="mt-3 text-xs text-slate-400 dark:text-slate-600">
            Schema last synced:{" "}
            {conn.schema_updated_at ? new Date(conn.schema_updated_at).toLocaleString() : "never"}
          </p>

          <div className="mt-3 flex gap-2">
            <Button size="sm" variant="secondary" onClick={() => onRefreshSchema(conn)} isLoading={refreshingId === conn.id}>
              <RefreshCw className="h-3.5 w-3.5" /> Refresh Schema
            </Button>
            <Button size="sm" variant="secondary" onClick={() => onEdit(conn)}>
              <Pencil className="h-3.5 w-3.5" /> Edit
            </Button>
            <Button size="sm" variant="danger" onClick={() => onDelete(conn)}>
              <Trash2 className="h-3.5 w-3.5" /> Remove
            </Button>
          </div>
        </Card>
      ))}
    </div>
  );
}
