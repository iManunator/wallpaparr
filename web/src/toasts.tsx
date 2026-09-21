import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

export type ToastKind = "ok" | "error" | "info";
export type Toast = { id: number; kind: ToastKind; text: string };

type ToastFn = (kind: ToastKind, text: string) => void;

const ToastContext = createContext<ToastFn>(() => undefined);

let nextId = 1;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const dismiss = useCallback((id?: number) => {
    setToasts((current) => (id == null ? [] : current.filter((toast) => toast.id !== id)));
  }, []);
  const notify = useCallback<ToastFn>((kind, text) => {
    const id = nextId++;
    setToasts((current) => [...current.slice(-4), { id, kind, text }]);
    window.setTimeout(() => {
      setToasts((current) => current.filter((toast) => toast.id !== id));
    }, 8000);
  }, []);
  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape" && toasts.length) {
        event.preventDefault();
        dismiss(toasts[toasts.length - 1]?.id);
      }
    }
    function onPointer(event: MouseEvent | PointerEvent) {
      if (!toasts.length) return;
      const target = event.target as HTMLElement | null;
      if (target?.closest(".toasts")) return;
      dismiss();
    }
    window.addEventListener("keydown", onKey);
    document.addEventListener("pointerdown", onPointer);
    return () => {
      window.removeEventListener("keydown", onKey);
      document.removeEventListener("pointerdown", onPointer);
    };
  }, [dismiss, toasts]);
  const value = useMemo(() => notify, [notify]);
  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="toasts" aria-live="polite" aria-relevant="additions">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`toast toast-${toast.kind}`}
            role={toast.kind === "error" ? "alert" : "status"}
          >
            <span>{toast.text}</span>
            <button
              type="button"
              className="toast-dismiss"
              aria-label="Close notification"
              onClick={() => dismiss(toast.id)}
            >
              ×
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToasts(): ToastFn {
  return useContext(ToastContext);
}
