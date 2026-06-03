export type RunGroup<T> = {
  key: string;
  runId: string | null;
  label: string;
  items: T[];
};

/** 按 run_id 分组；无 run_id 归入「其他」。FM 批次优先、按 run_id 降序。 */
export function buildRunGroups<T>(
  items: T[],
  getRunId: (item: T) => string | null | undefined
): RunGroup<T>[] {
  const map = new Map<string, T[]>();
  for (const item of items) {
    const key = getRunId(item) || "__none__";
    const list = map.get(key) || [];
    list.push(item);
    map.set(key, list);
  }
  const groups: RunGroup<T>[] = [];
  for (const [key, list] of Array.from(map.entries())) {
    const runId = key === "__none__" ? null : key;
    groups.push({
      key,
      runId,
      label: runId ? `批次 ${runId}` : "其他（无 run_id）",
      items: list,
    });
  }
  groups.sort((a, b) => {
    if (a.runId && !b.runId) return -1;
    if (!a.runId && b.runId) return 1;
    if (a.runId && b.runId) return b.runId.localeCompare(a.runId);
    return 0;
  });
  return groups;
}

export function toggleSetMember(set: Set<string>, id: string): Set<string> {
  const next = new Set(set);
  if (next.has(id)) next.delete(id);
  else next.add(id);
  return next;
}
