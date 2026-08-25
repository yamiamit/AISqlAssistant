import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Database } from "lucide-react";
import { useConnections } from "../context/ConnectionContext";
import * as chatApi from "../api/chat";
import ChatWindow from "../components/chat/ChatWindow";
import ChatInput from "../components/chat/ChatInput";
import ExampleQuestionChips from "../components/chat/ExampleQuestionChips";
import EmptyState from "../components/common/EmptyState";
import Spinner from "../components/common/Spinner";
import type { Message } from "../types";
import { Link } from "react-router-dom";

export default function ChatPage() {
  const { conversationId } = useParams();
  const navigate = useNavigate();
  const { activeConnectionId, connections, isLoading: connectionsLoading } = useConnections();

  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoadingConversation, setIsLoadingConversation] = useState(false);
  const [isTyping, setIsTyping] = useState(false);

  useEffect(() => {
    if (!conversationId) {
      setMessages([]);
      return;
    }
    setIsLoadingConversation(true);
    chatApi
      .getConversation(Number(conversationId))
      .then((conv) => setMessages(conv.messages))
      .catch(() => setMessages([]))
      .finally(() => setIsLoadingConversation(false));
  }, [conversationId]);

  async function handleSend(prompt: string) {
    if (!activeConnectionId) return;
    setIsTyping(true);
    try {
      const message = await chatApi.runQuery({
        prompt,
        db_connection_id: activeConnectionId,
        conversation_id: conversationId ? Number(conversationId) : null,
      });
      setMessages((prev) => [...prev, message]);
      if (!conversationId) {
        navigate(`/app/chat/${message.conversation_id}`, { replace: true });
      }
    } catch (err) {
      const fallback: Message = {
        id: Date.now(),
        conversation_id: conversationId ? Number(conversationId) : 0,
        prompt_text: prompt,
        generated_sql: null,
        explanation: null,
        result_columns: null,
        result_rows: null,
        row_count: null,
        execution_time_ms: null,
        chart_type: null,
        error_message: err instanceof Error ? err.message : "Something went wrong.",
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, fallback]);
    } finally {
      setIsTyping(false);
    }
  }

  if (connectionsLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Spinner />
      </div>
    );
  }

  const activeConnection = connections.find((c) => c.id === activeConnectionId);

  if (connections.length === 0) {
    return (
      <EmptyState
        icon={<Database className="h-8 w-8" />}
        title="Connect a database to get started"
        description="You need at least one connected PostgreSQL database before you can chat with your data."
        action={
          <Link to="/app/connections" className="text-sm font-medium text-indigo-600 hover:underline dark:text-indigo-400">
            Go to Database Connection →
          </Link>
        }
      />
    );
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 overflow-y-auto">
        {isLoadingConversation ? (
          <div className="flex h-full items-center justify-center">
            <Spinner />
          </div>
        ) : (
          <ChatWindow messages={messages} isTyping={isTyping} dbConnectionId={activeConnectionId} />
        )}
      </div>
      {activeConnection?.is_demo && <ExampleQuestionChips onPick={handleSend} disabled={isTyping} />}
      <ChatInput onSend={handleSend} disabled={isTyping} />
    </div>
  );
}
