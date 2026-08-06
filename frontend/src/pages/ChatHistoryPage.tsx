import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { MessagesSquare, Search, Trash2 } from "lucide-react";
import * as chatApi from "../api/chat";
import type { ConversationSummary } from "../types";
import Input from "../components/common/Input";
import Spinner from "../components/common/Spinner";
import EmptyState from "../components/common/EmptyState";
import Card from "../components/common/Card";

export default function ChatHistoryPage() {
  const navigate = useNavigate();
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [search, setSearch] = useState("");
  const [isLoading, setIsLoading] = useState(true);

  function load(query?: string) {
    setIsLoading(true);
    chatApi
      .listConversations(query || undefined)
      .then(setConversations)
      .finally(() => setIsLoading(false));
  }

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    const timeout = setTimeout(() => load(search), 300);
    return () => clearTimeout(timeout);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search]);

  async function handleDelete(e: React.MouseEvent, id: number) {
    e.stopPropagation();
    if (!confirm("Delete this conversation? This cannot be undone.")) return;
    await chatApi.deleteConversation(id);
    setConversations((prev) => prev.filter((c) => c.id !== id));
  }

  return (
    <div className="mx-auto max-w-3xl p-6">
      <h1 className="mb-4 text-lg font-semibold text-slate-900 dark:text-slate-100">Chat History</h1>

      <div className="relative mb-4">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
        <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search conversations..." className="pl-9" />
      </div>

      {isLoading ? (
        <div className="flex justify-center py-16">
          <Spinner />
        </div>
      ) : conversations.length === 0 ? (
        <EmptyState icon={<MessagesSquare className="h-8 w-8" />} title="No conversations yet" description="Start a new chat to see it here." />
      ) : (
        <div className="flex flex-col gap-2">
          {conversations.map((conv) => (
            <Card
              key={conv.id}
              className="flex cursor-pointer items-center justify-between px-4 py-3 hover:bg-slate-50 dark:hover:bg-slate-800/60"
              onClick={() => navigate(`/app/chat/${conv.id}`)}
            >
              <div>
                <p className="text-sm font-medium text-slate-900 dark:text-slate-100">{conv.title}</p>
                <p className="text-xs text-slate-500 dark:text-slate-500">{new Date(conv.updated_at).toLocaleString()}</p>
              </div>
              <button
                onClick={(e) => handleDelete(e, conv.id)}
                className="rounded-lg p-2 text-slate-400 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-950/50 dark:hover:text-red-400"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
