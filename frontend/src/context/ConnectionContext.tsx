import { createContext, useContext, useCallback, useEffect, useState, type ReactNode } from "react";
import * as connectionsApi from "../api/connections";
import type { DBConnection } from "../types";

interface ConnectionContextValue {
  connections: DBConnection[];
  activeConnectionId: number | null;
  setActiveConnectionId: (id: number | null) => void;
  isLoading: boolean;
  refresh: () => Promise<void>;
}

const ConnectionContext = createContext<ConnectionContextValue | undefined>(undefined);

// Shared across every dashboard page so "which database am I querying?"
// stays consistent between the Chat, Schema Viewer, and PDF Upload pages
// without each one re-fetching the connection list independently.
export function ConnectionProvider({ children }: { children: ReactNode }) {
  const [connections, setConnections] = useState<DBConnection[]>([]);
  const [activeConnectionId, setActiveConnectionIdState] = useState<number | null>(() => {
    const stored = localStorage.getItem("active_connection_id");
    return stored ? Number(stored) : null;
  });
  const [isLoading, setIsLoading] = useState(true);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    try {
      const list = await connectionsApi.listConnections();
      setConnections(list);
      setActiveConnectionIdState((current) => {
        if (current && list.some((c) => c.id === current)) return current;
        return list[0]?.id ?? null;
      });
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  function setActiveConnectionId(id: number | null) {
    setActiveConnectionIdState(id);
    if (id) localStorage.setItem("active_connection_id", String(id));
    else localStorage.removeItem("active_connection_id");
  }

  return (
    <ConnectionContext.Provider value={{ connections, activeConnectionId, setActiveConnectionId, isLoading, refresh }}>
      {children}
    </ConnectionContext.Provider>
  );
}

export function useConnections() {
  const ctx = useContext(ConnectionContext);
  if (!ctx) throw new Error("useConnections must be used within a ConnectionProvider");
  return ctx;
}
