import { seerrBadge } from "./lib/seerr";

export function SeerrBadge({
  libraryState,
  availability,
  source,
  className = "",
}: {
  libraryState?: string | null;
  availability?: string | null;
  source?: string | null;
  className?: string;
}) {
  const badge = seerrBadge(libraryState, availability, source);
  if (!badge) return null;
  return (
    <span
      className={`chrome-pill badge badge-seerr ${badge.id} ${className}`.trim()}
      title={`Seerr status: ${badge.label}`}
    >
      {badge.label}
    </span>
  );
}
