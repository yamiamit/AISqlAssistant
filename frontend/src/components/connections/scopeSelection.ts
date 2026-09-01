import type { SchemaTable } from "../../types";

/**
 * Tables that something selected points at, but which aren't selected themselves.
 *
 * Granting the referring table without its target produces a schema whose joins
 * can't run. The backend prunes those foreign keys before the AI ever sees them,
 * so nothing breaks at query time — the model simply never learns the
 * relationship, and questions spanning it quietly stop being answerable. That is
 * a reasonable thing to choose, but not a reasonable thing to choose by accident,
 * which is why it surfaces as a prompt rather than being auto-corrected.
 *
 * Returns a map of missing target table -> the selected tables referencing it.
 * Self-references and references to tables outside `tables` (already pruned, or
 * in another schema) are ignored: neither is something the user can act on here.
 */
export function findMissingReferences(
  tables: SchemaTable[],
  selected: ReadonlySet<string>
): Map<string, string[]> {
  const byTarget = new Map<string, string[]>();
  const known = new Set(tables.map((table) => table.name));

  for (const table of tables) {
    if (!selected.has(table.name)) continue;
    for (const fk of table.foreign_keys) {
      const target = fk.references_table;
      if (target === table.name || !known.has(target) || selected.has(target)) continue;
      const referrers = byTarget.get(target) ?? [];
      if (!referrers.includes(table.name)) referrers.push(table.name);
      byTarget.set(target, referrers);
    }
  }

  return byTarget;
}
