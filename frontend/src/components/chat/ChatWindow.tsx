import { useEffect, useRef } from "react";
import type { Message } from "../../types";
import MessageBubble from "./MessageBubble";
import TypingIndicator from "./TypingIndicator";
import EmptyState from "../common/EmptyState";
import { Sparkles } from "lucide-react";

interface ChatWindowProps {
  messages: Message[];
  isTyping: boolean;
  dbConnectionId: number | null;
}

export default function ChatWindow({ messages, isTyping, dbConnectionId }: ChatWindowProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  if (messages.length === 0 && !isTyping) {
    return (
      <EmptyState
        icon={<Sparkles className="h-8 w-8" />}
        title="Ask a question about your data"
        description='Try something like "Show top 10 customers by revenue" or "Monthly revenue trend for 2024".'
      />
    );
  }

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6 px-4 py-6">
      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} dbConnectionId={dbConnectionId} />
      ))}
      {isTyping && <TypingIndicator />}
      <div ref={bottomRef} />
    </div>
  );
}
