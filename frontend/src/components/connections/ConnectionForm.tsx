import { useState } from "react";
import clsx from "clsx";
import { CheckCircle2, XCircle } from "lucide-react";
import Input from "../common/Input";
import Button from "../common/Button";
import * as connectionsApi from "../../api/connections";
import type { DBConnectionInput } from "../../api/connections";
import type { DBConnection } from "../../types";

interface ConnectionFormProps {
  existing?: DBConnection;
  onSaved: () => void;
  onCancel: () => void;
}

export default function ConnectionForm({ existing, onSaved, onCancel }: ConnectionFormProps) {
  const [mode, setMode] = useState<"fields" | "string">("fields");
  const [name, setName] = useState(existing?.name ?? "");
  const [connectionString, setConnectionString] = useState("");
  const [host, setHost] = useState(existing?.host ?? "");
  const [port, setPort] = useState(existing?.port ?? 5432);
  const [databaseName, setDatabaseName] = useState(existing?.database_name ?? "");
  const [username, setUsername] = useState(existing?.username ?? "");
  const [password, setPassword] = useState("");

  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
  const [isTesting, setIsTesting] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function buildPayload(): DBConnectionInput {
    if (mode === "string") {
      return { name, connection_string: connectionString };
    }
    return { name, host, port, database_name: databaseName, username, password };
  }

  async function handleTest() {
    setError(null);
    setTestResult(null);
    setIsTesting(true);
    try {
      const result = await connectionsApi.testConnection(buildPayload());
      setTestResult(result);
    } catch (err) {
      setTestResult({ success: false, message: err instanceof Error ? err.message : "Test failed." });
    } finally {
      setIsTesting(false);
    }
  }

  async function handleSave() {
    setError(null);
    setIsSaving(true);
    try {
      if (existing) {
        await connectionsApi.updateConnection(existing.id, buildPayload());
      } else {
        await connectionsApi.createConnection(buildPayload());
      }
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save connection.");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <Input label="Connection name" value={name} onChange={(e) => setName(e.target.value)} placeholder="My Production DB" />

      <div className="flex gap-1 rounded-lg bg-slate-100 p-1 text-sm dark:bg-slate-800">
        {(["fields", "string"] as const).map((m) => (
          <button
            key={m}
            onClick={() => setMode(m)}
            className={clsx(
              "flex-1 rounded-md py-1.5 font-medium transition-colors",
              mode === m
                ? "bg-white text-slate-900 shadow-sm dark:bg-slate-700 dark:text-slate-100"
                : "text-slate-500 dark:text-slate-400"
            )}
          >
            {m === "fields" ? "Host / Port / etc." : "Connection String"}
          </button>
        ))}
      </div>

      {mode === "fields" ? (
        <div className="grid grid-cols-2 gap-3">
          <Input label="Host" value={host} onChange={(e) => setHost(e.target.value)} placeholder="localhost" />
          <Input label="Port" type="number" value={port} onChange={(e) => setPort(Number(e.target.value))} />
          <Input
            label="Database name"
            value={databaseName}
            onChange={(e) => setDatabaseName(e.target.value)}
            className="col-span-2"
          />
          <Input label="Username" value={username} onChange={(e) => setUsername(e.target.value)} />
          <Input
            label={existing ? "Password (leave blank to keep current)" : "Password"}
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>
      ) : (
        <Input
          label="Connection string"
          value={connectionString}
          onChange={(e) => setConnectionString(e.target.value)}
          placeholder="postgresql://username:password@host:5432/database"
        />
      )}

      {testResult && (
        <div
          className={clsx(
            "flex items-center gap-2 rounded-lg px-3 py-2 text-sm",
            testResult.success
              ? "bg-green-50 text-green-700 dark:bg-green-950/50 dark:text-green-300"
              : "bg-red-50 text-red-700 dark:bg-red-950/50 dark:text-red-300"
          )}
        >
          {testResult.success ? <CheckCircle2 className="h-4 w-4" /> : <XCircle className="h-4 w-4" />}
          {testResult.message}
        </div>
      )}
      {error && <div className="text-sm text-red-600 dark:text-red-400">{error}</div>}

      <div className="mt-2 flex justify-end gap-2">
        <Button variant="secondary" onClick={onCancel}>
          Cancel
        </Button>
        <Button variant="secondary" onClick={handleTest} isLoading={isTesting}>
          Test Connection
        </Button>
        <Button onClick={handleSave} isLoading={isSaving}>
          {existing ? "Save Changes" : "Save Connection"}
        </Button>
      </div>
    </div>
  );
}
