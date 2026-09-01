import { useEffect, useMemo, useState } from "react";
import { Check, Copy, KeyRound, Link2, ShieldCheck } from "lucide-react";
import * as connectionsApi from "../../api/connections";
import type { AccessScript, DBConnection, SchemaTable } from "../../types";
import { findMissingReferences } from "./scopeSelection";
import Button from "../common/Button";
import Input from "../common/Input";
import Spinner from "../common/Spinner";
import ErrorBanner from "../common/ErrorBanner";

interface ScopedAccessPanelProps {
  connection: DBConnection;
  onScoped: () => void;
  onDismiss: () => void;
}

/**
 * Walks the user through swapping a connection's credentials for a role that
 * can only SELECT from the tables they choose.
 *
 * The app never runs the script itself — creating a role needs privileges far
 * beyond a query tool's business, and handing over SQL to read first is a much
 * smaller thing to ask someone to trust. Step 2 is a copy box for that reason,
 * not because the automation was too hard.
 *
 * The chosen table list is deliberately not persisted anywhere. Once the user
 * pastes the new DSN back, introspection runs as the new role and the cached
 * schema *becomes* the allowed set — a second stored list would only be a copy
 * that can drift, and one that would lie for anyone who picks tables here and
 * never gets around to running the script.
 */
export default function ScopedAccessPanel({ connection, onScoped, onDismiss }: ScopedAccessPanelProps) {
  const [tables, setTables] = useState<SchemaTable[] | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [script, setScript] = useState<AccessScript | null>(null);
  const [connectionString, setConnectionString] = useState("");
  const [isLoadingSchema, setIsLoadingSchema] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [copied, setCopied] = useState<"script" | "dsn" | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    connectionsApi
      .getSchema(connection.id)
      .then((schema) => {
        setTables(schema.tables);
        // Everything on by default: the picker is for *narrowing*, and starting
        // from nothing makes the safe-but-tedious path the default one.
        setSelected(new Set(schema.tables.map((table) => table.name)));
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Could not read this connection's tables."))
      .finally(() => setIsLoadingSchema(false));
  }, [connection.id]);

  const missingReferences = useMemo(
    () => findMissingReferences(tables ?? [], selected),
    [tables, selected]
  );

  function toggle(name: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  }

  function addMissingReferences() {
    setSelected((prev) => new Set([...prev, ...missingReferences.keys()]));
  }

  async function handleGenerate() {
    setError(null);
    setIsGenerating(true);
    try {
      const generated = await connectionsApi.generateAccessScript(connection.id, [...selected]);
      setScript(generated);
      setConnectionString(generated.connection_string);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not generate the script.");
    } finally {
      setIsGenerating(false);
    }
  }

  async function handleCopy(text: string, which: "script" | "dsn") {
    await navigator.clipboard.writeText(text);
    setCopied(which);
    window.setTimeout(() => setCopied(null), 1500);
  }

  async function handleSaveConnectionString() {
    setError(null);
    setIsSaving(true);
    try {
      // The ordinary update path: it re-parses the DSN, re-encrypts the
      // password, and re-introspects — which is what actually narrows the
      // schema, since introspection runs as whatever role just connected.
      await connectionsApi.updateConnection(connection.id, { connection_string: connectionString });
      onScoped();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save the new connection string.");
    } finally {
      setIsSaving(false);
    }
  }

  const allSelected = tables !== null && selected.size === tables.length;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-start gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-600 dark:border-slate-800 dark:bg-slate-800/50 dark:text-slate-300">
        <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-indigo-600 dark:text-indigo-400" />
        <span>
          The SQL guards decide what <em>kind</em> of query runs, never which tables it touches —{" "}
          <code className="rounded bg-slate-200 px-1 text-xs dark:bg-slate-700">SELECT password_hash FROM users</code>{" "}
          is a perfectly valid read. Only the database can draw that line, so this step swaps your credentials
          for a role that can read the tables you pick and nothing else.
        </span>
      </div>

      {error && <ErrorBanner message={error} />}

      <section>
        <div className="mb-2 flex items-center justify-between gap-2">
          <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">1. Choose what the AI can see</h3>
          {tables && tables.length > 0 && !script && (
            <button
              onClick={() => setSelected(allSelected ? new Set() : new Set(tables.map((t) => t.name)))}
              className="text-xs font-medium text-indigo-600 hover:underline dark:text-indigo-400"
            >
              {allSelected ? "Clear all" : "Select all"}
            </button>
          )}
        </div>

        {isLoadingSchema ? (
          <div className="flex justify-center py-6">
            <Spinner />
          </div>
        ) : !tables || tables.length === 0 ? (
          <p className="text-xs text-slate-500 dark:text-slate-400">
            No tables are known for this connection yet — refresh its schema first.
          </p>
        ) : script ? (
          <p className="text-xs text-slate-500 dark:text-slate-400">
            {script.tables.length} table{script.tables.length === 1 ? "" : "s"}: {script.tables.join(", ")}.{" "}
            <button
              onClick={() => setScript(null)}
              className="font-medium text-indigo-600 hover:underline dark:text-indigo-400"
            >
              Change selection
            </button>
          </p>
        ) : (
          <>
            <div className="max-h-52 overflow-y-auto rounded-lg border border-slate-200 dark:border-slate-700">
              {tables.map((table) => (
                <label
                  key={table.name}
                  className="flex cursor-pointer items-center gap-2 border-b border-slate-100 px-3 py-2 last:border-b-0 hover:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-800/50"
                >
                  <input
                    type="checkbox"
                    checked={selected.has(table.name)}
                    onChange={() => toggle(table.name)}
                    className="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500 dark:border-slate-600 dark:bg-slate-800"
                  />
                  <span className="text-sm text-slate-800 dark:text-slate-200">{table.name}</span>
                  <span className="ml-auto text-xs text-slate-400 dark:text-slate-500">
                    {table.columns.length} column{table.columns.length === 1 ? "" : "s"}
                  </span>
                </label>
              ))}
            </div>

            {missingReferences.size > 0 && (
              <div className="mt-2 flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-300">
                <Link2 className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                <span>
                  {[...missingReferences.entries()].slice(0, 3).map(([target, referrers]) => (
                    <span key={target} className="block">
                      <strong>{referrers.join(", ")}</strong> reference{referrers.length === 1 ? "s" : ""}{" "}
                      <strong>{target}</strong>, which isn't selected — those joins won't be available.
                    </span>
                  ))}
                  {missingReferences.size > 3 && (
                    <span className="block">…and {missingReferences.size - 3} more.</span>
                  )}
                  <button
                    onClick={addMissingReferences}
                    className="mt-1 font-medium underline underline-offset-2 hover:no-underline"
                  >
                    Add {missingReferences.size} referenced table{missingReferences.size === 1 ? "" : "s"}
                  </button>
                </span>
              </div>
            )}
          </>
        )}
      </section>

      <section>
        <h3 className="mb-1 text-sm font-semibold text-slate-900 dark:text-slate-100">2. Generate the script</h3>
        {!script ? (
          <>
            <p className="mb-2 text-xs text-slate-500 dark:text-slate-400">
              Creates a role granted <code className="rounded bg-slate-100 px-1 dark:bg-slate-800">SELECT</code> on
              the {selected.size} selected table{selected.size === 1 ? "" : "s"} — and nothing else.
            </p>
            <Button onClick={handleGenerate} isLoading={isGenerating} disabled={selected.size === 0}>
              <KeyRound className="h-4 w-4" /> Generate script
            </Button>
          </>
        ) : (
          <>
            <div className="relative">
              <pre className="max-h-56 overflow-auto rounded-lg border border-slate-200 bg-slate-900 p-3 text-xs leading-relaxed text-slate-100 dark:border-slate-700">
                {script.script}
              </pre>
              <Button
                size="sm"
                variant="secondary"
                className="absolute right-2 top-2"
                onClick={() => handleCopy(script.script, "script")}
              >
                {copied === "script" ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
                {copied === "script" ? "Copied" : "Copy"}
              </Button>
            </div>
            <p className="mt-2 text-xs text-amber-600 dark:text-amber-500">
              This password is shown once and is never stored — copy the script before closing.
            </p>
          </>
        )}
      </section>

      {script && (
        <>
          <section>
            <h3 className="mb-1 text-sm font-semibold text-slate-900 dark:text-slate-100">3. Run it on your database</h3>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Paste it into <code className="rounded bg-slate-100 px-1 dark:bg-slate-800">psql</code> (or any client)
              as a user that can <code className="rounded bg-slate-100 px-1 dark:bg-slate-800">CREATE ROLE</code> —
              usually the database owner. Read it first; it only creates a role and grants{" "}
              <code className="rounded bg-slate-100 px-1 dark:bg-slate-800">SELECT</code>.
            </p>
          </section>

          <section>
            <h3 className="mb-1 text-sm font-semibold text-slate-900 dark:text-slate-100">
              4. Switch this connection over
            </h3>
            <p className="mb-2 text-xs text-slate-500 dark:text-slate-400">
              Pre-filled with the new role's connection string. Saving it re-reads the schema as{" "}
              <code className="rounded bg-slate-100 px-1 dark:bg-slate-800">{script.role}</code>, so anything it
              can't read disappears from the AI's view.
            </p>
            <Input
              label="New connection string"
              value={connectionString}
              onChange={(e) => setConnectionString(e.target.value)}
              placeholder="postgresql://user:password@host:5432/dbname"
            />
            <div className="mt-2 flex gap-2">
              <Button onClick={handleSaveConnectionString} isLoading={isSaving} disabled={!connectionString.trim()}>
                Save and re-read schema
              </Button>
              <Button variant="secondary" onClick={() => handleCopy(script.connection_string, "dsn")}>
                {copied === "dsn" ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                {copied === "dsn" ? "Copied" : "Copy string"}
              </Button>
            </div>
          </section>
        </>
      )}

      <div className="border-t border-slate-200 pt-3 dark:border-slate-800">
        <button
          onClick={onDismiss}
          className="text-xs text-slate-500 underline underline-offset-2 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
        >
          Continue with full access
        </button>
        <span className="ml-1 text-xs text-slate-400 dark:text-slate-500">
          — queries still run read-only, and you can come back to this any time.
        </span>
      </div>
    </div>
  );
}
