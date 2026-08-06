import { useEffect, useState } from "react";
import { RefreshCw, TableProperties } from "lucide-react";
import { useConnections } from "../context/ConnectionContext";
import * as connectionsApi from "../api/connections";
import SchemaTable from "../components/schema/SchemaTable";
import Button from "../components/common/Button";
import Spinner from "../components/common/Spinner";
import ErrorBanner from "../components/common/ErrorBanner";
import EmptyState from "../components/common/EmptyState";
import type { SchemaResponse } from "../types";

export default function SchemaViewerPage() {
  const { connections, activeConnectionId } = useConnections();
  const [schema, setSchema] = useState<SchemaResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const activeConnection = connections.find((c) => c.id === activeConnectionId);

  useEffect(() => {
    if (!activeConnectionId) return;
    setIsLoading(true);
    setError(null);
    connectionsApi
      .getSchema(activeConnectionId)
      .then(setSchema)
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load schema."))
      .finally(() => setIsLoading(false));
  }, [activeConnectionId]);

  async function handleRefresh() {
    if (!activeConnectionId) return;
    setIsRefreshing(true);
    setError(null);
    try {
      const next = await connectionsApi.refreshSchema(activeConnectionId);
      setSchema(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not refresh schema.");
    } finally {
      setIsRefreshing(false);
    }
  }

  if (!activeConnectionId) {
    return (
      <EmptyState
        icon={<TableProperties className="h-8 w-8" />}
        title="No database connected"
        description="Connect a database first to view its tables, columns, primary keys, and foreign keys."
      />
    );
  }

  return (
    <div className="mx-auto max-w-5xl p-6">
      <div className="mb-5 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Schema Viewer</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">{activeConnection?.name}</p>
        </div>
        <Button variant="secondary" onClick={handleRefresh} isLoading={isRefreshing}>
          <RefreshCw className="h-4 w-4" /> Refresh Schema
        </Button>
      </div>

      {error && (
        <div className="mb-4">
          <ErrorBanner message={error} />
        </div>
      )}

      {isLoading ? (
        <div className="flex justify-center py-16">
          <Spinner />
        </div>
      ) : schema && schema.tables.length > 0 ? (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {schema.tables.map((table) => (
            <SchemaTable key={table.name} table={table} />
          ))}
        </div>
      ) : (
        <EmptyState title="No tables found" description="This database doesn't have any tables in the public schema yet." />
      )}
    </div>
  );
}
