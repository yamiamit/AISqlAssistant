import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Plus, Database, Sparkles } from "lucide-react";
import { useConnections } from "../context/ConnectionContext";
import * as connectionsApi from "../api/connections";
import ConnectionList from "../components/connections/ConnectionList";
import ConnectionForm from "../components/connections/ConnectionForm";
import Modal from "../components/common/Modal";
import Button from "../components/common/Button";
import EmptyState from "../components/common/EmptyState";
import Spinner from "../components/common/Spinner";
import ErrorBanner from "../components/common/ErrorBanner";
import type { DBConnection } from "../types";

export default function ConnectDatabasePage() {
  const { connections, isLoading, refresh, setActiveConnectionId } = useConnections();
  const navigate = useNavigate();
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<DBConnection | undefined>(undefined);
  const [refreshingId, setRefreshingId] = useState<number | null>(null);
  const [isTryingDemo, setIsTryingDemo] = useState(false);
  const [demoError, setDemoError] = useState<string | null>(null);

  function openCreate() {
    setEditing(undefined);
    setFormOpen(true);
  }

  function openEdit(conn: DBConnection) {
    setEditing(conn);
    setFormOpen(true);
  }

  async function handleSaved() {
    setFormOpen(false);
    await refresh();
  }

  async function handleDelete(conn: DBConnection) {
    if (!confirm(`Remove connection "${conn.name}"? This cannot be undone.`)) return;
    await connectionsApi.deleteConnection(conn.id);
    await refresh();
  }

  async function handleRefreshSchema(conn: DBConnection) {
    setRefreshingId(conn.id);
    try {
      await connectionsApi.refreshSchema(conn.id);
    } finally {
      setRefreshingId(null);
    }
  }

  async function handleTryDemo() {
    setDemoError(null);
    setIsTryingDemo(true);
    try {
      const demoConnection = await connectionsApi.createDemoConnection();
      await refresh();
      setActiveConnectionId(demoConnection.id);
      navigate("/app");
    } catch (err) {
      setDemoError(
        err instanceof Error ? err.message : "Couldn't set up the sample database. Please try again."
      );
    } finally {
      setIsTryingDemo(false);
    }
  }

  return (
    <div className="mx-auto max-w-4xl p-6">
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-slate-900 dark:text-slate-100">Database Connections</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Connect your own PostgreSQL database — schema is discovered automatically.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={handleTryDemo} isLoading={isTryingDemo}>
            <Sparkles className="h-4 w-4" /> Try with sample data
          </Button>
          <Button onClick={openCreate}>
            <Plus className="h-4 w-4" /> Connect Database
          </Button>
        </div>
      </div>

      {demoError && (
        <div className="mb-5">
          <ErrorBanner message={demoError} />
        </div>
      )}

      {isLoading ? (
        <div className="flex justify-center py-16">
          <Spinner />
        </div>
      ) : connections.length === 0 ? (
        <EmptyState
          icon={<Database className="h-8 w-8" />}
          title="No databases connected yet"
          description="Connect a PostgreSQL database to start asking questions in natural language."
          action={
            <div className="flex gap-2">
              <Button variant="secondary" onClick={handleTryDemo} isLoading={isTryingDemo}>
                <Sparkles className="h-4 w-4" /> Try with sample data
              </Button>
              <Button onClick={openCreate}>
                <Plus className="h-4 w-4" /> Connect Database
              </Button>
            </div>
          }
        />
      ) : (
        <ConnectionList
          connections={connections}
          onEdit={openEdit}
          onDelete={handleDelete}
          onRefreshSchema={handleRefreshSchema}
          refreshingId={refreshingId}
        />
      )}

      {formOpen && (
        <Modal title={editing ? "Edit Connection" : "Connect Database"} onClose={() => setFormOpen(false)} wide>
          <ConnectionForm existing={editing} onSaved={handleSaved} onCancel={() => setFormOpen(false)} />
        </Modal>
      )}
    </div>
  );
}
