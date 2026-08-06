import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Play, Star, Trash2 } from "lucide-react";
import * as savedQueriesApi from "../api/savedQueries";
import * as chatApi from "../api/chat";
import { useConnections } from "../context/ConnectionContext";
import type { SavedQuery } from "../types";
import Card from "../components/common/Card";
import Button from "../components/common/Button";
import Spinner from "../components/common/Spinner";
import EmptyState from "../components/common/EmptyState";

export default function SavedQueriesPage() {
  const navigate = useNavigate();
  const { activeConnectionId } = useConnections();
  const [queries, setQueries] = useState<SavedQuery[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [runningId, setRunningId] = useState<number | null>(null);

  useEffect(() => {
    savedQueriesApi
      .listSavedQueries()
      .then(setQueries)
      .finally(() => setIsLoading(false));
  }, []);

  async function handleDelete(id: number) {
    if (!confirm("Delete this saved query?")) return;
    await savedQueriesApi.deleteSavedQuery(id);
    setQueries((prev) => prev.filter((q) => q.id !== id));
  }

  async function handleRun(query: SavedQuery) {
    const connectionId = query.db_connection_id ?? activeConnectionId;
    if (!connectionId) return;
    setRunningId(query.id);
    try {
      const message = await chatApi.runQuery({ prompt: query.prompt_text, db_connection_id: connectionId });
      navigate(`/app/chat/${message.conversation_id}`);
    } finally {
      setRunningId(null);
    }
  }

  return (
    <div className="mx-auto max-w-3xl p-6">
      <h1 className="mb-4 text-lg font-semibold text-slate-900 dark:text-slate-100">Saved Queries</h1>

      {isLoading ? (
        <div className="flex justify-center py-16">
          <Spinner />
        </div>
      ) : queries.length === 0 ? (
        <EmptyState
          icon={<Star className="h-8 w-8" />}
          title="No saved queries yet"
          description='Save a query from any chat response by clicking "Save Query".'
        />
      ) : (
        <div className="flex flex-col gap-2">
          {queries.map((q) => (
            <Card key={q.id} className="p-4">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">{q.name}</p>
                  <p className="mt-0.5 truncate text-xs text-slate-500 dark:text-slate-500">{q.prompt_text}</p>
                  <pre className="mt-2 max-h-20 overflow-auto rounded bg-slate-100 p-2 text-[11px] text-slate-600 dark:bg-slate-800 dark:text-slate-400">
                    {q.sql_text}
                  </pre>
                </div>
                <div className="flex shrink-0 gap-2">
                  <Button size="sm" onClick={() => handleRun(q)} isLoading={runningId === q.id}>
                    <Play className="h-3.5 w-3.5" /> Run
                  </Button>
                  <Button size="sm" variant="danger" onClick={() => handleDelete(q.id)}>
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
