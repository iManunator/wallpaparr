import { api, type JobSnapshot } from "./api";
import { errorToast, generateToast, motionToast } from "./messages";

export type { JobSnapshot };

export function idleJob(): JobSnapshot {
  return {
    id: null,
    kind: null,
    status: "idle",
    total: 0,
    done: 0,
    current: null,
    message: "",
    created: [],
    failed: [],
    skipped: [],
    error: null,
    result: null,
    percent: 0,
  };
}

export function isActiveJob(job?: JobSnapshot | null): boolean {
  return job?.status === "queued" || job?.status === "running";
}

export function jobLabel(job?: JobSnapshot | null): string {
  if (!job || job.status === "idle") return "";
  const kind = job.kind === "motion" ? "Motion bake" : job.kind === "cron" ? "Scheduled generate" : "Generate";
  if (isActiveJob(job)) {
    const count = job.total > 0 ? `${job.done}/${job.total}` : "starting";
    const title = job.current ? ` · ${job.current}` : "";
    return `${kind} ${count}${title}`;
  }
  return job.message || kind;
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

export async function waitForJob(id: string, onTick?: (job: JobSnapshot) => void): Promise<JobSnapshot> {
  for (;;) {
    const job = await api.job(id);
    onTick?.(job);
    if (!isActiveJob(job)) return job;
    await sleep(350);
  }
}

export async function runJob(
  body: Record<string, unknown>,
  onTick?: (job: JobSnapshot) => void,
): Promise<JobSnapshot> {
  const started = await api.startJob(body);
  onTick?.(started);
  if (!started.id || !isActiveJob(started)) return started;
  return waitForJob(started.id, onTick);
}

export function jobToast(job: JobSnapshot): { kind: "ok" | "error" | "info"; text: string } {
  if (job.status === "error") {
    return { kind: "error", text: job.error || job.message || "Job failed" };
  }
  if (job.status === "cancelled") {
    return { kind: "info", text: job.message || "Cancelled" };
  }
  const result = (job.result || {}) as {
    message?: string;
    count?: number;
    warnings?: string[];
    generated?: string[];
    style?: string;
  };
  const message = job.message || result.message;
  if (job.kind === "motion") {
    return motionToast({
      message,
      count: Number(result.count ?? job.created.length),
      generated: result.generated || job.created,
      style: result.style,
    });
  }
  return generateToast({
    message,
    count: Number(result.count ?? job.created.length),
    warnings: result.warnings,
  });
}

export function failedJobToast(err: unknown): { kind: "error"; text: string } {
  return errorToast(err, "Job failed");
}
