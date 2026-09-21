export type Identified = {
  jellyfin_id?: string | null;
  tmdb_id?: string | null;
  imdb_id?: string | null;
  title: string;
  year?: number | null;
};

function idsOf(item: Identified): Set<string> {
  return new Set(
    [item.jellyfin_id, item.tmdb_id, item.imdb_id]
      .filter(Boolean)
      .map((value) => String(value).toLowerCase()),
  );
}

export function shouldSkipExisting(
  catalog: Identified[],
  item: Identified,
  skipExisting: boolean,
): boolean {
  if (!skipExisting) return false;
  const wanted = idsOf(item);
  if (wanted.size) {
    return catalog.some((row) => [...idsOf(row)].some((id) => wanted.has(id)));
  }
  return catalog.some(
    (row) =>
      row.title.trim().toLowerCase() === item.title.trim().toLowerCase() &&
      (item.year == null || row.year === item.year),
  );
}
