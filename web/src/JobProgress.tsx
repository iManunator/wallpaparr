import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, type JobSnapshot } from "./lib/api";
import { failedJobToast, idleJob, isActiveJob, jobLabel, jobToast, runJob } from "./lib/jobs";
import { useToasts } from "./toasts";

type JobContextValue = {
  job: JobSnapshot;
  busy: boolean;
  run: (body: Record<string, unknown>) => Promise<JobSnapshot>;
  cancel: () => Promise<void>;
};

const JobContext = createContext<JobContextValue>({
  job: idleJob(),
  busy: false,
  run: async () => idleJob(),
  cancel: async () => undefined,
});

export function JobProvider({ children }: { children: ReactNode }) {
  const notify = useToasts();
  const [job, setJob] = useState<JobSnapshot>(idleJob);
  const run = useCallback(
    async (body: Record<string, unknown>) => {
      try {
        const final = await runJob(body, setJob);
        const toast = jobToast(final);
        notify(toast.kind, toast.text);
        return final;
      } catch (err) {
        const toast = failedJobToast(err);
        notify(toast.kind, toast.text);
        throw err;
      }
    },
    [notify],
  );

  const cancel = useCallback(async () => {
    if (!job.id || !isActiveJob(job)) return;
    try {
      const updated = await api.cancelJob(job.id);
      setJob(updated);
    } catch (err) {
      const toast = failedJobToast(err);
      notify(toast.kind, toast.text);
    }
  }, [job, notify]);

  useEffect(() => {
    let cancelled = false;
    let timer = 0;
    async function tick() {
      try {
        const latest = await api.jobsLatest();
        if (!cancelled) setJob(latest && typeof latest.status === "string" ? latest : idleJob());
        const wait = isActiveJob(latest) ? 350 : 2500;
        timer = window.setTimeout(tick, wait);
      } catch {
        timer = window.setTimeout(tick, 4000);
      }
    }
    void tick();
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, []);

  const value = useMemo(
    () => ({ job, busy: isActiveJob(job), run, cancel }),
    [job, run, cancel],
  );
  return <JobContext.Provider value={value}>{children}</JobContext.Provider>;
}

export function useJobs(): JobContextValue {
  return useContext(JobContext);
}

export function JobProgress({ job }: { job?: JobSnapshot | null }) {
  const ctx = useJobs();
  const snapshot = job ?? ctx.job;
  if (!snapshot || typeof snapshot.status !== "string" || snapshot.status === "idle" || snapshot.status === "done" || snapshot.status === "cancelled") {
    return null;
  }
  const active = isActiveJob(snapshot);
  const percent = Math.max(0, Math.min(100, snapshot.percent || 0));
  const cancelling = Boolean(snapshot.cancel_requested);
  return (
    <div className={`job-progress ${snapshot.status}`} role="status" aria-live="polite" aria-busy={active}>
      <div className="job-progress-bar" aria-hidden="true">
        <span style={{ width: `${percent}%` }} />
      </div>
      <div className="job-progress-row">
        <p>
          <strong>{active ? `${snapshot.done}/${snapshot.total || "?"}` : snapshot.status}</strong>
          {snapshot.current ? ` · ${snapshot.current}` : ""}
          {snapshot.message && snapshot.message !== `${snapshot.done}/${snapshot.total}`
            ? ` — ${snapshot.message}`
            : ""}
        </p>
        {active && snapshot.id ? (
          <button
            type="button"
            className="btn ghost job-progress-cancel"
            disabled={cancelling}
            onClick={() => void ctx.cancel()}
          >
            {cancelling ? "Cancelling…" : "Cancel"}
          </button>
        ) : null}
      </div>
    </div>
  );
}
