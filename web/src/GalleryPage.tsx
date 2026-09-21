import { useEffect, useState } from "react";
import { ConfirmDialog } from "./ConfirmDialog";
import { FullscreenViewer, wallpaperSlide } from "./FullscreenViewer";
import { api } from "./lib/api";
import { deleteAllCopy, deleteSelectedCopy, formatDeleteToast } from "./lib/gallery";
import type { WallpaperRecord } from "./lib/layout";
import { errorToast } from "./lib/messages";
import { queueBadges } from "./lib/queues";
import { badgeClass } from "./lib/watch";
import { useToasts } from "./toasts";

type ConfirmState =
  | { kind: "selected"; ids: string[]; titles: string[]; items: WallpaperRecord[] }
  | { kind: "all" };

export function GalleryPage({ onEdit }: { onEdit: () => void }) {
  const notify = useToasts();
  const [items, setItems] = useState<WallpaperRecord[]>([]);
  const [error, setError] = useState("");
  const [showHidden, setShowHidden] = useState(false);
  const [search, setSearch] = useState("");
  const [viewer, setViewer] = useState<number | null>(null);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [busy, setBusy] = useState(false);
  const [confirm, setConfirm] = useState<ConfirmState | null>(null);

  async function refresh() {
    try {
      setItems(await api.gallery());
      setError("");
    } catch (err) {
      const toast = errorToast(err, "Could not load gallery");
      setError(toast.text);
    }
  }
  useEffect(() => {
    void refresh();
  }, []);

  const query = search.trim().toLowerCase();
  const visible = items.filter(
    (item) => (showHidden || !item.hidden) && (!query || item.title.toLowerCase().includes(query)),
  );
  const slides = visible.map(wallpaperSlide);
  const selectedItems = items.filter((item) => selected.has(item.id));
  const allVisibleSelected = visible.length > 0 && visible.every((item) => selected.has(item.id));
  const selectedCopy = deleteSelectedCopy(confirm?.kind === "selected" ? confirm.items : selectedItems);
  const allCopy = deleteAllCopy(items);

  function toggleSelect(id: string) {
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function selectAllVisible() {
    setSelected(new Set(visible.map((item) => item.id)));
  }

  function clearSelection() {
    setSelected(new Set());
  }

  async function flagItem(item: WallpaperRecord, body: { pinned?: boolean; hidden?: boolean }) {
    setBusy(true);
    try {
      await api.flag(item.id, body);
      await refresh();
    } catch (err) {
      const toast = errorToast(err, "Could not update gallery item");
      notify(toast.kind, toast.text);
    } finally {
      setBusy(false);
    }
  }

  function askDeleteItems(target: WallpaperRecord[]) {
    if (!target.length) return;
    setConfirm({
      kind: "selected",
      ids: target.map((item) => item.id),
      titles: target.map((item) => item.title),
      items: target,
    });
  }

  function askDeleteAll() {
    if (allCopy.empty) {
      notify("info", "Gallery is already empty.");
      return;
    }
    setConfirm({ kind: "all" });
  }

  async function runSelectedDelete() {
    if (confirm?.kind !== "selected") return;
    const ids = confirm.ids;
    setBusy(true);
    try {
      const out = ids.length === 1 ? await api.deleteGallery(ids[0]) : await api.deleteGalleryMany(ids);
      notify("ok", formatDeleteToast(out, `Deleted ${out.count} wallpaper${out.count === 1 ? "" : "s"}.`));
      if (out.missing?.length) notify("info", `${out.missing.length} selected ${out.missing.length === 1 ? "id was" : "ids were"} already gone.`);
      if (out.errors?.length) notify("error", out.errors[0]);
      setSelected((current) => {
        const next = new Set(current);
        ids.forEach((id) => next.delete(id));
        return next;
      });
      closeViewerIfGone(ids);
      setConfirm(null);
      await refresh();
    } catch (err) {
      const toast = errorToast(err, "Could not delete");
      notify(toast.kind, toast.text);
    } finally {
      setBusy(false);
    }
  }

  async function runDeleteAll(includePins: boolean) {
    setBusy(true);
    try {
      const out = await api.deleteGalleryAll({ includePins });
      const kind = out.count ? "ok" : "info";
      notify(kind, formatDeleteToast(out, includePins ? "Gallery cleared." : "Unpinned wallpapers deleted."));
      if (out.errors?.length) notify("error", out.errors[0]);
      setSelected(new Set());
      setViewer(null);
      setConfirm(null);
      await refresh();
    } catch (err) {
      const toast = errorToast(err, "Could not delete gallery");
      notify(toast.kind, toast.text);
    } finally {
      setBusy(false);
    }
  }

  function closeViewerIfGone(ids: string[]) {
    if (viewer === null) return;
    const remaining = visible.filter((item) => !ids.includes(item.id));
    setViewer(remaining.length ? Math.min(viewer, remaining.length - 1) : null);
  }

  return (
    <section>
      <h1>Gallery</h1>
      <p className="lede">
        Generated stills and optional parallax VIDEO loops served to Projectivy. Pin a title to keep it in rotation,
        mark never-show so it drops out of every queue, or delete a still (and its companion MP4) from disk. Delete all
        skips pins unless you choose the explicit danger option. Click a still for a full-screen motion preview (baked
        VIDEO when present, otherwise layered CSS: artwork pans, title and badges stay locked). Grid thumbs stay still.
      </p>
      <div className="gallery-toolbar">
        <button className="btn" onClick={onEdit}>
          Open editor
        </button>
        <input
          type="search"
          className="gallery-search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search titles…"
          aria-label="Search gallery"
        />
        <span className="gallery-count">{visible.length} wallpaper{visible.length === 1 ? "" : "s"}</span>
        <label className="inline">
          <input type="checkbox" checked={showHidden} onChange={(e) => setShowHidden(e.target.checked)} /> Show never-show
        </label>
        <button className="btn ghost" disabled={!visible.length || allVisibleSelected || busy} onClick={selectAllVisible}>
          Select all
        </button>
        <button className="btn ghost" disabled={!selected.size || busy} onClick={clearSelection}>
          Clear selection
        </button>
        <span className="gallery-count" aria-live="polite">
          {selected.size} selected
        </span>
        <button
          className="btn danger"
          disabled={!selected.size || busy}
          onClick={() => askDeleteItems(selectedItems)}
        >
          Delete selected
        </button>
        <button className="btn danger" disabled={!items.length || busy} onClick={askDeleteAll}>
          Delete all
        </button>
      </div>
      {error && <p className="error">{error}</p>}
      {!items.length && !error ? (
        <p className="muted">No wallpapers yet. Generate a batch, then come back to pin, hide, or clear the library.</p>
      ) : null}
      <div className="thumb-grid">
        {visible.map((item, index) => (
          <article className={`thumb ${selected.has(item.id) ? "selected" : ""}`} key={item.id}>
            <label className="thumb-select inline">
              <input
                type="checkbox"
                checked={selected.has(item.id)}
                onChange={() => toggleSelect(item.id)}
                aria-label={`Select ${item.title}`}
              />
            </label>
            <button type="button" className="thumb-hit" onClick={() => setViewer(index)} aria-label={`View ${item.title} full screen`}>
              <img src={api.wallpaperImage(item.layout, item.filename)} alt={item.title} />
            </button>
            <div className="meta">
              <strong>{item.title}</strong>
              <div className="muted">
                {item.year} · {item.layout}
                {item.has_video ? ` · ${item.parallax_style || "motion"}` : ""}
              </div>
              <div>
                {queueBadges(item).map((badge) => (
                  <span className={badgeClass(badge)} key={badge}>
                    {badge}
                  </span>
                ))}
              </div>
              <div className="row thumb-actions">
                <button className="btn ghost tiny" disabled={busy} onClick={() => flagItem(item, { pinned: !item.pinned })}>
                  {item.pinned ? "Unpin" : "Pin"}
                </button>
                <button className="btn ghost tiny" disabled={busy} onClick={() => flagItem(item, { hidden: !item.hidden })}>
                  {item.hidden ? "Allow again" : "Never show"}
                </button>
                <button className="btn danger tiny" disabled={busy} onClick={() => askDeleteItems([item])}>
                  Delete
                </button>
              </div>
            </div>
          </article>
        ))}
      </div>
      {viewer !== null && (
        <FullscreenViewer
          items={slides}
          index={viewer}
          onClose={() => setViewer(null)}
          onIndex={setViewer}
          onPin={(slide) => {
            const item = visible.find((row) => row.id === slide.id);
            if (item) void flagItem(item, { pinned: !item.pinned });
          }}
          onHide={(slide) => {
            const item = visible.find((row) => row.id === slide.id);
            if (item) void flagItem(item, { hidden: !item.hidden });
          }}
          onDelete={(slide) => {
            const item = visible.find((row) => row.id === slide.id);
            if (item) askDeleteItems([item]);
          }}
        />
      )}
      {confirm?.kind === "selected" && (
        <ConfirmDialog
          title={selectedCopy.title}
          body={selectedCopy.body}
          note={selectedCopy.note}
          confirmLabel={selectedCopy.confirmLabel}
          busy={busy}
          onCancel={() => setConfirm(null)}
          onConfirm={() => void runSelectedDelete()}
        />
      )}
      {confirm?.kind === "all" && (
        <ConfirmDialog
          title={allCopy.title}
          body={allCopy.body}
          note={allCopy.note}
          confirmLabel={allCopy.confirmLabel}
          extraLabel={allCopy.extraLabel}
          busy={busy}
          onCancel={() => setConfirm(null)}
          onConfirm={allCopy.confirmLabel ? () => void runDeleteAll(false) : undefined}
          onExtra={allCopy.extraLabel ? () => void runDeleteAll(true) : undefined}
        />
      )}
    </section>
  );
}
