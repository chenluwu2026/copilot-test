const STORAGE_KEY = "aims-inbox-selection";

export type InboxTab = "draft" | "approved";

type InboxSelectionStore = Record<InboxTab, string[]>;

function emptyStore(): InboxSelectionStore {
  return { draft: [], approved: [] };
}

export function loadInboxSelection(): InboxSelectionStore {
  if (typeof window === "undefined") return emptyStore();
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return emptyStore();
    const parsed = JSON.parse(raw) as Partial<InboxSelectionStore>;
    return {
      draft: Array.isArray(parsed.draft) ? parsed.draft : [],
      approved: Array.isArray(parsed.approved) ? parsed.approved : [],
    };
  } catch {
    return emptyStore();
  }
}

export function saveInboxSelection(tab: InboxTab, ids: string[]) {
  if (typeof window === "undefined") return;
  const store = loadInboxSelection();
  store[tab] = ids;
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify(store));
}

export function idsToSet(ids: string[]): Set<string> {
  return new Set(ids);
}
