import { useEffect, useRef } from "react";

export function ConfirmDialog({
  title,
  body,
  note,
  confirmLabel,
  extraLabel,
  busy,
  onConfirm,
  onExtra,
  onCancel,
}: {
  title: string;
  body: string;
  note?: string;
  confirmLabel?: string;
  extraLabel?: string | null;
  busy?: boolean;
  onConfirm?: () => void;
  onExtra?: () => void;
  onCancel: () => void;
}) {
  const cancelRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    cancelRef.current?.focus();
    function onKey(event: KeyboardEvent) {
      if (event.key !== "Escape") return;
      event.preventDefault();
      event.stopImmediatePropagation();
      if (!busy) onCancel();
    }
    window.addEventListener("keydown", onKey, true);
    return () => window.removeEventListener("keydown", onKey, true);
  }, [busy, onCancel]);
  return (
    <div
      className="confirm-backdrop"
      role="presentation"
      onClick={() => {
        if (!busy) onCancel();
      }}
    >
      <div
        className="confirm-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="confirm-title"
        aria-describedby="confirm-body"
        onClick={(event) => event.stopPropagation()}
      >
        <h2 id="confirm-title">{title}</h2>
        <p id="confirm-body">{body}</p>
        {note ? <p className="confirm-note">{note}</p> : null}
        <div className="row confirm-actions">
          <button ref={cancelRef} type="button" className="btn ghost" disabled={busy} onClick={onCancel}>
            Cancel
          </button>
          {confirmLabel && onConfirm ? (
            <button type="button" className="btn danger fill" disabled={busy} onClick={onConfirm}>
              {confirmLabel}
            </button>
          ) : null}
          {extraLabel && onExtra ? (
            <button type="button" className="btn danger fill strong" disabled={busy} onClick={onExtra}>
              {extraLabel}
            </button>
          ) : null}
        </div>
      </div>
    </div>
  );
}
