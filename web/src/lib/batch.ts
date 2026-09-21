export type BatchFlags = {
  skip_existing: boolean;
  replace_existing: boolean;
  refresh_status?: boolean;
  cleanup: boolean;
  ids?: string[];
  skip_ids?: string[];
};

export function describeBatchFlags(flags: BatchFlags): string {
  const bits: string[] = [];
  if (flags.replace_existing) {
    bits.push("Replace overwrites matching Jellyfin / TMDB / IMDb ids (skip is ignored).");
  } else if (flags.skip_existing) {
    bits.push("Skip leaves titles already generated for this layout in place.");
    if (flags.refresh_status) {
      bits.push(
        "Refresh status re-bakes stills when watch state or availability changes (e.g. unwatched → watched, requestable → available).",
      );
    }
  } else {
    bits.push("Every matching title is rendered again as a new still.");
  }
  if (flags.cleanup) {
    bits.push("Cleanup deletes stills in this layout whose ids are no longer in the source list.");
  }
  if (flags.ids?.length) {
    bits.push(`Only ${flags.ids.length} id${flags.ids.length === 1 ? "" : "s"} will be generated.`);
  }
  if (flags.skip_ids?.length) {
    bits.push(`${flags.skip_ids.length} id${flags.skip_ids.length === 1 ? "" : "s"} will be ignored.`);
  }
  return bits.join(" ");
}

export function effectiveSkipExisting(skipExisting: boolean, replaceExisting: boolean): boolean {
  return skipExisting && !replaceExisting;
}
