import { watchBadge } from "./lib/watch";

export function WatchBadge({
  state,
  className = "",
}: {
  state?: string | null;
  className?: string;
}) {
  const badge = watchBadge(state);
  if (!badge) return null;
  return (
    <span
      className={`chrome-pill badge badge-watch ${badge.id} ${className}`.trim()}
      title={`Watch status: ${badge.label}`}
    >
      {badge.label}
    </span>
  );
}
