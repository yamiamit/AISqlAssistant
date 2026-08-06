import { useState } from "react";
import Modal from "../common/Modal";
import Input from "../common/Input";
import Button from "../common/Button";
import * as savedQueriesApi from "../../api/savedQueries";

interface SaveQueryModalProps {
  promptText: string;
  sqlText: string;
  dbConnectionId: number | null;
  onClose: () => void;
  onSaved: () => void;
}

export default function SaveQueryModal({ promptText, sqlText, dbConnectionId, onClose, onSaved }: SaveQueryModalProps) {
  const [name, setName] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSave() {
    if (!name.trim()) {
      setError("Give this query a name.");
      return;
    }
    setIsSaving(true);
    setError(null);
    try {
      await savedQueriesApi.createSavedQuery({
        name: name.trim(),
        prompt_text: promptText,
        sql_text: sqlText,
        db_connection_id: dbConnectionId,
      });
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save query.");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <Modal
      title="Save Query"
      onClose={onClose}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={handleSave} isLoading={isSaving}>
            Save
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-3">
        <Input
          label="Name"
          autoFocus
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. Monthly Revenue"
        />
        {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}
      </div>
    </Modal>
  );
}
