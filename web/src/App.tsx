import { useEffect, useState, type CSSProperties } from "react";
import { EditorPage } from "./EditorPage";
import { GalleryPage } from "./GalleryPage";
import { api } from "./lib/api";
import { type AppSettings, type CronJob } from "./lib/layout";
import { describeBatchFlags } from "./lib/batch";
import { errorToast, providerToast } from "./lib/messages";
import { clampIntensity, defaultDuration, describeMotion, intensityFromPreset, motionPreviewVars, motionSeedKey, nearestMotionPreset, type MotionStyle } from "./lib/motion";
import { formatOpsTime, QUEUE_LABELS, TASTE_PRESETS } from "./lib/queues";
import { SampleLockedChrome, WallpaperStage } from "./WallpaperStage";
import { TonightPage } from "./TonightPage";
import { JobProgress, JobProvider, useJobs } from "./JobProgress";
import { ToastProvider, useToasts } from "./toasts";
import "./styles/app.css";

type Page = "tonight" | "gallery" | "editor" | "generate" | "dashboard" | "settings";

const SEERR_CATEGORIES: Array<{ id: string; label: string }> = [
  { id: "trending", label: "Trending" },
  { id: "movies_popular", label: "Popular movies" },
  { id: "tv_popular", label: "Popular series" },
  { id: "movies_upcoming", label: "Upcoming movies" },
  { id: "tv_upcoming", label: "Upcoming series" },
];

const EMPTY_SETTINGS: AppSettings = {
  public_base_url: "http://127.0.0.1:8787",
  timezone: "UTC",
  motion_wallpapers: false,
  motion_quality: "light",
  motion_style: "parallax",
  motion_intensity: 0.55,
  motion_duration: 15,
  motion_fps: 24,
  overwrite_existing: false,
  editor_theme: "cinema",
  motion_preset: "balanced",
  light_leak: true,
  motion_vary: true,
  motion_edge_fade: true,
  motion_edge_fade_seconds: 1.0,
  motion_fly_in: true,
  motion_fly_in_seconds: 1.0,
  taste_profile: "tonight",
  taste_weights: { unwatched: 30, continue_watching: 20, watched: 15, newly_added: 20, seerr_trending: 15 },
  overlays_enabled: false,
  overlay_clock: true,
  overlays: [],
  title_display: "auto",
  jellyfin: {},
  jellyseerr: {},
  tmdb: {},
  omdb: {},
  cron_jobs: [],
};

const PAGES: Page[] = ["tonight", "gallery", "editor", "generate", "dashboard", "settings"];

export function App() {
  return (
    <ToastProvider>
      <JobProvider>
        <AppShell />
      </JobProvider>
    </ToastProvider>
  );
}

function AppShell() {
  const [page, setPage] = useState<Page>("tonight");
  const [theme, setTheme] = useState("cinema");
  const [editorLayout, setEditorLayout] = useState<string | undefined>();
  useEffect(() => {
    api
      .settings()
      .then((settings) => setTheme(settings.editor_theme || "cinema"))
      .catch(() => undefined);
  }, []);
  function go(next: Page, layout?: string) {
    setEditorLayout(next === "editor" ? layout : undefined);
    setPage(next);
  }
  return (
    <div className="app" data-theme={theme}>
      <nav className="nav">
        <h2 className="brand">Wallpaparr</h2>
        <div className="brand-sub">*arr live wallpapers for Projectivy</div>
        {PAGES.map((id) => (
          <button key={id} className={page === id ? "active" : ""} onClick={() => go(id)}>
            {id === "tonight" ? "Tonight" : id[0].toUpperCase() + id.slice(1)}
          </button>
        ))}
      </nav>
      <main className="main">
        <JobProgress />
        {page === "tonight" && (
          <TonightPage
            onEdit={(layout) => go("editor", layout)}
            onGenerate={() => go("generate")}
            onSettings={() => go("settings")}
            onGallery={() => go("gallery")}
          />
        )}
        {page === "gallery" && <GalleryPage onEdit={() => go("editor")} />}
        {page === "editor" && <EditorPage initialLayout={editorLayout} />}
        {page === "generate" && <GeneratePage />}
        {page === "dashboard" && <DashboardPage />}
        {page === "settings" && <SettingsPage onTheme={setTheme} />}
      </main>
    </div>
  );
}

function csvToIds(value: string): string[] {
  return value
    .split(/[,\s]+/)
    .map((part) => part.trim())
    .filter(Boolean);
}

function GeneratePage() {
  const { run, busy } = useJobs();
  const [layouts, setLayouts] = useState<string[]>([]);
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [form, setForm] = useState({
    layout: "Netflix Hero",
    source: "demo",
    seerr_category: "trending",
    limit: 8,
    skip_existing: true,
    replace_existing: false,
    refresh_status: true,
    cleanup: false,
    motion: false,
    ids: "",
    skip_ids: "",
  });
  const [result, setResult] = useState("");
  const [showAdvanced, setShowAdvanced] = useState(false);
  useEffect(() => {
    api.layouts().then((names) => {
      setLayouts(names);
      const preferred = names.includes("Netflix Hero") ? "Netflix Hero" : names[0];
      if (preferred) setForm((f) => ({ ...f, layout: preferred }));
    });
    api
      .settings()
      .then((loaded) => {
        setSettings(loaded);
        const preferredSource = loaded.jellyfin?.url ? "jellyfin" : loaded.jellyseerr?.url ? "jellyseerr" : "demo";
        setForm((f) => ({ ...f, motion: Boolean(loaded.motion_wallpapers), source: preferredSource }));
      })
      .catch(() => undefined);
  }, []);
  const style = (settings?.motion_style || "parallax") as MotionStyle;
  const intensity = intensityFromPreset(settings?.motion_preset) || clampIntensity(settings?.motion_intensity ?? 0.55);
  const duration = settings?.motion_duration || defaultDuration(settings?.motion_quality || "light");
  const motionVars = motionPreviewVars(style, intensity, Number(duration), {
    vary: settings?.motion_vary !== false,
    seed: motionSeedKey("demo-jf-4", "Signal Country"),
    preset: settings?.motion_preset,
  });
  async function setMotionVary(checked: boolean) {
    const current = settings || EMPTY_SETTINGS;
    const next = { ...current, motion_vary: checked };
    setSettings(next);
    try {
      await api.saveSettings(next);
    } catch {
      /* preview still updates locally */
    }
  }
  return (
    <section>
      <h1>Generate</h1>
      <p className="lede">
        Batch cinematic stills from Jellyfin, Jellyseerr, or the built-in demo catalog (NASA / NARA / Library of Congress stills). Skip already-rendered titles by Jellyfin / TMDB / IMDb id, replace them in place, or bake optional parallax VIDEO loops for Projectivy. Layout <code>title_display</code> paints a movie/series logo when one exists.
      </p>
      <div className="generate-grid">
        <div className="card">
          <label>Layout / collection</label>
          <select value={form.layout} onChange={(e) => setForm({ ...form, layout: e.target.value })}>
            {layouts.map((name) => (
              <option key={name}>{name}</option>
            ))}
          </select>
          <label style={{ marginTop: 12 }}>Source</label>
          <select value={form.source} onChange={(e) => setForm({ ...form, source: e.target.value })}>
            <option value="demo">Demo catalog</option>
            <option value="jellyfin">Jellyfin</option>
            <option value="jellyseerr">Jellyseerr / Seerr</option>
            <option value="all">All configured</option>
          </select>
          {(form.source === "jellyseerr" || form.source === "all") && (
            <>
              <label style={{ marginTop: 12 }}>Jellyseerr category</label>
              <select value={form.seerr_category} onChange={(e) => setForm({ ...form, seerr_category: e.target.value })}>
                {SEERR_CATEGORIES.map((cat) => (
                  <option key={cat.id} value={cat.id}>{cat.label}</option>
                ))}
              </select>
            </>
          )}
          <label style={{ marginTop: 12 }}>Limit</label>
          <input
            type="number"
            min={1}
            max={200}
            value={form.limit}
            onChange={(e) => setForm({ ...form, limit: Number(e.target.value) })}
          />
          <label>
            <input type="checkbox" checked={form.motion} onChange={(e) => setForm({ ...form, motion: e.target.checked })} />{" "}
            Bake parallax / motion VIDEO (ffmpeg)
          </label>
          <button className="btn ghost tiny" style={{ marginTop: 10 }} onClick={() => setShowAdvanced(!showAdvanced)}>
            {showAdvanced ? "Hide advanced options" : "Show advanced options"}
          </button>
          {showAdvanced && (
            <>
              <label style={{ marginTop: 12 }}>Only these media ids (Jellyfin / TMDB / IMDb, comma-separated)</label>
              <input value={form.ids} onChange={(e) => setForm({ ...form, ids: e.target.value })} placeholder="demo-jf-1, 90001, tt123" />
              <label style={{ marginTop: 12 }}>Skip these media ids</label>
              <input value={form.skip_ids} onChange={(e) => setForm({ ...form, skip_ids: e.target.value })} placeholder="leave blank to skip none extra" />
              <label style={{ marginTop: 12 }}><input type="checkbox" checked={form.skip_existing} disabled={form.replace_existing} onChange={(e) => setForm({ ...form, skip_existing: e.target.checked })} /> Skip titles already generated (IMDb / TMDB / Jellyfin id)</label>
              <label><input type="checkbox" checked={form.replace_existing} onChange={(e) => setForm({ ...form, replace_existing: e.target.checked, skip_existing: e.target.checked ? false : form.skip_existing })} /> Replace / overwrite same show</label>
              <label>
                <input
                  type="checkbox"
                  checked={form.refresh_status}
                  disabled={form.replace_existing}
                  onChange={(e) => setForm({ ...form, refresh_status: e.target.checked })}
                />{" "}
                Refresh when watch / availability changes
              </label>
              <label><input type="checkbox" checked={form.cleanup} onChange={(e) => setForm({ ...form, cleanup: e.target.checked })} /> Cleanup titles no longer in the source list</label>
              <p className="muted flag-help">{describeBatchFlags({ skip_existing: form.skip_existing, replace_existing: form.replace_existing, refresh_status: form.refresh_status, cleanup: form.cleanup, ids: csvToIds(form.ids), skip_ids: csvToIds(form.skip_ids) })}</p>
              <button
                className="btn ghost tiny"
                disabled={busy}
                onClick={async () => {
                  try {
                    const out = await run({ kind: "motion", layout: form.layout });
                    setResult(out.message || String((out.result as { message?: string } | null)?.message || ""));
                  } catch (err) {
                    setResult(errorToast(err, "Motion bake failed").text);
                  }
                }}
              >
                Bake motion for this layout
              </button>
            </>
          )}
          <p className="muted">{describeMotion(style, intensity, Number(duration))}. Stills always remain; Projectivy only gets <code>videoUrl</code> when an MP4 exists. Intensity preset: {settings?.motion_preset || "balanced"}{settings?.light_leak ? " · light leak" : ""}{settings?.motion_vary !== false ? " · per-title variety" : ""}.</p>
          <div className="row" style={{ marginTop: 16 }}>
            <button
              className="btn"
              disabled={busy}
              onClick={async () => {
                try {
                  const out = await run({
                    kind: "generate",
                    layout: form.layout,
                    source: form.source,
                    seerr_category: form.seerr_category,
                    limit: Math.min(200, Math.max(1, Number(form.limit) || 8)),
                    skip_existing: form.skip_existing,
                    replace_existing: form.replace_existing,
                    refresh_status: form.refresh_status,
                    cleanup: form.cleanup,
                    motion: form.motion,
                    ids: csvToIds(form.ids),
                    skip_ids: csvToIds(form.skip_ids),
                  });
                  setResult(out.message || String((out.result as { message?: string } | null)?.message || ""));
                } catch (err) {
                  setResult(errorToast(err, "Generate failed").text);
                }
              }}
            >
              Run batch
            </button>
          </div>
          {result && <p className="status">{result}</p>}
        </div>
        <div className="card">
          <h3>Motion preview</h3>
          <p className="muted">See {settings?.motion_preset || "balanced"} {style} on demo art before you bake ffmpeg loops.</p>
          <label>
            <input
              type="checkbox"
              checked={settings?.motion_vary !== false}
              onChange={(e) => void setMotionVary(e.target.checked)}
            />{" "}
            Vary motion slightly per wallpaper
          </label>
          <p className="muted">Mild seeded pan / intensity / phase drift so each title feels a bit different. Same title rebakes the same loop. Off is the exact CSS-matched path. Default on.</p>
          <WallpaperStage
            className="generate-preview"
            wrapClassName="canvas-wrap generate-preview"
            artSrc={api.mediaArtwork("demo-jf-4")}
            artAlt="Signal Country motion preview"
            motionOn
            motionVars={motionVars as CSSProperties}
            lightLeak={Boolean(settings?.light_leak)}
          />
        </div>
      </div>
    </section>
  );
}

function DashboardPage() {
  const [data, setData] = useState<Record<string, any> | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    api.dashboard().then(setData).catch((err) => setError(errorToast(err, "Could not load dashboard").text));
  }, []);
  if (!data) return <p>{error || "Loading…"}</p>;
  const gallery = data.gallery || {};
  const cron = data.cron || {};
  const providers = data.providers || {};
  return (
    <section>
      <h1>Health</h1>
      <p className="lede">Last cron, gallery size, motion preset, and whether Jellyfin / Seerr keys are configured. Demo mode is always healthy.</p>
      {error && <p className="error">{error}</p>}
      <div className="dash-grid">
        <article className="card">
          <h3>Gallery</h3>
          <p className="dash-stat">{gallery.count ?? 0}</p>
          <p className="muted">{gallery.videos ?? 0} VIDEO · {gallery.pinned ?? 0} pinned · {gallery.hidden ?? 0} never-show</p>
        </article>
        <article className="card">
          <h3>Cron</h3>
          <p className="dash-stat">{formatOpsTime(cron.last?.at)}</p>
          <p className="muted">{cron.jobs ?? 0} jobs · last generate {formatOpsTime(cron.last_generate?.at)}</p>
          {Array.isArray(cron.errors) && cron.errors.length > 0 && (
            <p className="error" style={{ marginTop: 8 }}>
              {cron.errors.length === 1
                ? `“${cron.errors[0].name}” has a bad cron expression (${cron.errors[0].cron}) — it is not scheduled.`
                : `${cron.errors.length} enabled jobs have invalid cron expressions and are not scheduled.`}
            </p>
          )}
        </article>
        <article className="card">
          <h3>Motion</h3>
          <p className="dash-stat">{data.motion?.preset || "balanced"}</p>
          <p className="muted">{data.motion?.style} · {data.motion?.quality}{data.motion?.light_leak ? " · leak" : ""}{data.motion?.vary !== false ? " · variety" : ""}</p>
        </article>
        <article className="card">
          <h3>Taste</h3>
          <p className="dash-stat">{data.taste?.profile || "tonight"}</p>
          <p className="muted">Plugin pick mode “Tonight’s mix” uses this profile.</p>
        </article>
      </div>
      <div className="grid two" style={{ marginTop: 16 }}>
        {["jellyfin", "jellyseerr", "tmdb", "demo"].map((name) => {
          const row = providers[name] || {};
          return (
            <article className="card" key={name}>
              <h3>{name}</h3>
              <p>{row.configured ? "Configured" : "Not configured"}</p>
              <p className="muted">Last test {formatOpsTime(row.last_test?.at)}</p>
            </article>
          );
        })}
      </div>
    </section>
  );
}

function SettingsPage({ onTheme }: { onTheme: (theme: string) => void }) {
  const notify = useToasts();
  const { run, busy } = useJobs();
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [msg, setMsg] = useState("");
  const [layouts, setLayouts] = useState<string[]>([]);
  const [showAdvanced, setShowAdvanced] = useState(false);
  useEffect(() => {
    api.settings().then((loaded) => setSettings({ ...EMPTY_SETTINGS, ...loaded })).catch(() => setSettings(EMPTY_SETTINGS));
    api.layouts().then(setLayouts).catch(() => undefined);
  }, []);
  if (!settings) return <p>Loading…</p>;
  function patch(section: "jellyfin" | "jellyseerr" | "tmdb" | "omdb", key: string, value: string) {
    setSettings({
      ...settings!,
      [section]: { ...(settings![section] || {}), [key]: value },
    });
  }
  const cronJobs: CronJob[] = settings.cron_jobs.length ? settings.cron_jobs : [];
  function defaultCronJob(name = "Schedule"): CronJob {
    return {
      name,
      enabled: false,
      cron: "0 4 * * *",
      layout: layouts[0] || "Netflix Hero",
      source: "jellyfin",
      seerr_category: "trending",
      skip_existing: true,
      replace_existing: false,
      refresh_status: false,
      cleanup: true,
      motion: false,
      limit: 20,
      ids: [],
      skip_ids: [],
    };
  }
  function setCronAt(index: number, next: CronJob) {
    const list = cronJobs.slice();
    list[index] = next;
    setSettings({ ...settings!, cron_jobs: list });
  }
  function addCronJob(seed?: Partial<CronJob>) {
    // If nothing's been saved yet, the on-screen "Schedule 1" is only a
    // placeholder — keep it as the real first entry instead of discarding it.
    const base = cronJobs.length ? cronJobs : [defaultCronJob("Schedule 1")];
    setSettings({
      ...settings!,
      cron_jobs: [...base, { ...defaultCronJob(`Schedule ${base.length + 1}`), ...seed }],
    });
  }
  function removeCronJob(index: number) {
    setSettings({ ...settings!, cron_jobs: cronJobs.filter((_, i) => i !== index) });
  }
  const preset = settings.motion_preset || nearestMotionPreset(settings.motion_intensity);
  const intensity = intensityFromPreset(preset);
  const duration = Number(settings.motion_duration || defaultDuration(settings.motion_quality));
  const style = (settings.motion_style || "parallax") as MotionStyle;
  const weights: Record<string, number> = {
    ...Object.fromEntries(Object.keys(QUEUE_LABELS).map((id) => [id, 0])),
    ...(settings.taste_weights || TASTE_PRESETS[settings.taste_profile || "tonight"]),
  };
  const totalWeight = Object.values(weights).reduce((sum, w) => sum + Number(w || 0), 0);
  const motionVars = motionPreviewVars(style, intensity, duration, {
    vary: settings.motion_vary !== false,
    seed: motionSeedKey("demo-jf-1", "Northlight"),
    preset: settings.motion_preset,
  });
  async function testConnection(name: "jellyfin" | "jellyseerr" | "tmdb") {
    try {
      const draft = settings![name] || {};
      const result = (await api.testProvider(name, {
        url: String(draft.url || ""),
        api_key: String(draft.api_key || ""),
        user_id: String((draft as { user_id?: string }).user_id || ""),
      })) as { ok?: boolean; message?: string; error?: string };
      const toast = providerToast(result);
      notify(toast.kind, toast.text);
      setMsg(toast.text);
    } catch (err) {
      const toast = errorToast(err, `Could not test ${name}`);
      notify(toast.kind, toast.text);
      setMsg(toast.text);
    }
  }
  return (
    <section>
      <h1>Settings</h1>
      <p className="lede">Provider keys stay in config.json on the server. This form never commits secrets. Plugin pick modes, filters, and VIDEO preference live on the TV; generation, taste, motion presets, and overlay hooks live here.</p>
      <button className="btn ghost tiny" style={{ marginBottom: 16 }} onClick={() => setShowAdvanced(!showAdvanced)}>
        {showAdvanced ? "Hide advanced settings" : "Show advanced settings"}
      </button>
      <div className="grid two">
        <div className="card">
          <h3>Jellyfin</h3>
          <label>URL</label>
          <input value={settings.jellyfin.url || ""} onChange={(e) => patch("jellyfin", "url", e.target.value)} placeholder="http://192.168.1.10:8096" />
          <label>API key</label>
          <input
            type="password"
            autoComplete="off"
            value={settings.jellyfin.api_key || ""}
            onChange={(e) => patch("jellyfin", "api_key", e.target.value)}
            placeholder="saved on the server"
          />
          <label>User id (optional)</label>
          <input value={settings.jellyfin.user_id || ""} onChange={(e) => patch("jellyfin", "user_id", e.target.value)} />
          <button className="btn ghost tiny" style={{ marginTop: 10 }} onClick={() => testConnection("jellyfin")}>Test Jellyfin</button>
        </div>
        <div className="card">
          <h3>Jellyseerr / Seerr</h3>
          <label>URL</label>
          <input value={settings.jellyseerr.url || ""} onChange={(e) => patch("jellyseerr", "url", e.target.value)} placeholder="http://192.168.1.10:5055" />
          <label>API key</label>
          <input
            type="password"
            autoComplete="off"
            value={settings.jellyseerr.api_key || ""}
            onChange={(e) => patch("jellyseerr", "api_key", e.target.value)}
            placeholder="saved on the server"
          />
          <button className="btn ghost tiny" style={{ marginTop: 10 }} onClick={() => testConnection("jellyseerr")}>Test Seerr</button>
        </div>
        <div className="card">
          <h3>Parallax / live motion</h3>
          <label>
            <input
              type="checkbox"
              checked={settings.motion_wallpapers}
              onChange={(e) => setSettings({ ...settings, motion_wallpapers: e.target.checked })}
            />{" "}
            Generate VIDEO loops by default (still IMAGE is always kept)
          </label>
          <label>Quality</label>
          <select value={settings.motion_quality} onChange={(e) => setSettings({ ...settings, motion_quality: e.target.value })}>
            <option value="light">Light</option>
            <option value="standard">Standard</option>
            <option value="cinematic">Cinematic</option>
          </select>
          <p className="muted">Sets default duration and bitrate. Light ~8s/2.8 Mbps, Standard ~12s/4 Mbps, Cinematic ~16s/5.5 Mbps (slower encode). More tuning under Advanced settings.</p>
        </div>
        <div className="card">
          <h3>Taste profile</h3>
          <p className="muted">Weights how often each queue is picked for Projectivy's plugin pick-mode "Tonight's mix" and this app's Tonight page. Must add up to 100% or less — each slider stops at what's left.</p>
          <div className="row" style={{ alignItems: "flex-end" }}>
            <div style={{ flex: 1 }}>
              <label>Profile</label>
              <select
                value={settings.taste_profile || "tonight"}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    taste_profile: e.target.value,
                    taste_weights: TASTE_PRESETS[e.target.value] || settings.taste_weights,
                  })
                }
              >
                {Object.keys(TASTE_PRESETS).map((id) => (
                  <option key={id} value={id}>{id}</option>
                ))}
              </select>
            </div>
            <button
              className="btn ghost tiny"
              onClick={() =>
                setSettings({
                  ...settings,
                  taste_profile: "tonight",
                  taste_weights: TASTE_PRESETS.tonight,
                })
              }
            >
              Reset to default
            </button>
          </div>
          <p className={`taste-total ${totalWeight >= 100 ? "at-limit" : ""}`}>
            {totalWeight}% allocated{totalWeight < 100 ? ` · ${100 - totalWeight}% unused (won't pick anything the rest of the time)` : " · fully allocated"}
          </p>
          <div className="taste-weights">
            {Object.entries(weights || {}).map(([id, weight]) => {
              const others = totalWeight - Number(weight || 0);
              const sliderMax = Math.max(0, 100 - others);
              return (
                <div className="taste-row" key={id}>
                  <label>{QUEUE_LABELS[id] || id} ({weight}%)</label>
                  <input
                    type="range"
                    min={0}
                    max={sliderMax}
                    value={Math.min(Number(weight || 0), sliderMax)}
                    onChange={(e) =>
                      setSettings({
                        ...settings,
                        taste_weights: { ...weights, [id]: Number(e.target.value) },
                      })
                    }
                  />
                </div>
              );
            })}
          </div>
        </div>
        {showAdvanced && (
        <>
        <div className="card">
          <h3>Serving</h3>
          <label>Public base URL (what the TV plugin should use)</label>
          <input
            value={settings.public_base_url}
            onChange={(e) => setSettings({ ...settings, public_base_url: e.target.value })}
            placeholder="http://192.168.1.10:8787"
          />
          <label>Timezone</label>
          <input value={settings.timezone} onChange={(e) => setSettings({ ...settings, timezone: e.target.value })} />
        </div>
        <div className="card">
          <h3>Advanced motion tuning</h3>
          <label>Motion style</label>
          <select value={settings.motion_style || "parallax"} onChange={(e) => setSettings({ ...settings, motion_style: e.target.value })}>
            <option value="parallax">Parallax</option>
            <option value="kenburns">Ken Burns</option>
            <option value="drift">Drift</option>
          </select>
          <p className="muted">Artwork stays locked — only the background moves. Parallax drifts, Ken Burns zooms, Drift slow-pans.</p>
          <label>Intensity preset</label>
          <select
            value={preset}
            onChange={(e) =>
              setSettings({
                ...settings,
                motion_preset: e.target.value,
                motion_intensity: intensityFromPreset(e.target.value),
              })
            }
          >
            <option value="subtle">Subtle</option>
            <option value="balanced">Balanced</option>
            <option value="cinematic">Cinematic</option>
            <option value="bold">Bold</option>
          </select>
          <label>
            <input
              type="checkbox"
              checked={Boolean(settings.light_leak)}
              onChange={(e) => setSettings({ ...settings, light_leak: e.target.checked })}
            />{" "}
            Light-leak layer on parallax VIDEO
          </label>
          <label>
            <input
              type="checkbox"
              checked={settings.motion_vary !== false}
              onChange={(e) => setSettings({ ...settings, motion_vary: e.target.checked })}
            />{" "}
            Vary motion slightly per wallpaper
          </label>
          <p className="muted">Default on. Each bake/preview gets a mild seeded pan direction, intensity jitter, start phase, and style drift inside Subtle / Balanced / Cinematic / Bold. Same title is stable. Off restores the exact CSS-matched ease/amplitude path.</p>
          <label>
            <input
              type="checkbox"
              checked={settings.motion_edge_fade !== false}
              onChange={(e) => setSettings({ ...settings, motion_edge_fade: e.target.checked })}
            />{" "}
            Fade to black at clip start/end
          </label>
          <p className="muted">Default on. Projectivy tears down and recreates its video player on every wallpaper swap with a hard cut. A short fade to/from black at each baked MP4's edges masks that cut instead of showing it mid-scene. Off bakes the clip at full brightness throughout.</p>
          <label>Fade duration seconds (0.1–2.5)</label>
          <input
            type="number"
            min={0.1}
            max={2.5}
            step={0.05}
            disabled={settings.motion_edge_fade === false}
            value={settings.motion_edge_fade_seconds ?? 1.0}
            onChange={(e) => setSettings({ ...settings, motion_edge_fade_seconds: Number(e.target.value) })}
          />
          <label>
            <input
              type="checkbox"
              checked={Boolean(settings.motion_fly_in)}
              onChange={(e) => setSettings({ ...settings, motion_fly_in: e.target.checked })}
            />{" "}
            Fly-in intro (experimental)
          </label>
          <p className="muted">On by default. Adds a fast zoom-in swoop at the very start of the clip that eases out smoothly into the normal parallax drift — no visible cut between the two motions.</p>
          <label>Fly-in duration seconds (0.2–4)</label>
          <input
            type="number"
            min={0.2}
            max={4}
            step={0.1}
            disabled={!settings.motion_fly_in}
            value={settings.motion_fly_in_seconds ?? 1.0}
            onChange={(e) => setSettings({ ...settings, motion_fly_in_seconds: Number(e.target.value) })}
          />
          <label>Loop duration seconds (blank = longer quality / intensity default, 2–24s)</label>
          <input
            type="number"
            min={2}
            max={24}
            value={settings.motion_duration ?? ""}
            onChange={(e) =>
              setSettings({
                ...settings,
                motion_duration: e.target.value === "" ? null : Number(e.target.value),
              })
            }
          />
          <label>FPS</label>
          <input
            type="number"
            min={12}
            max={30}
            value={settings.motion_fps || 24}
            onChange={(e) => setSettings({ ...settings, motion_fps: Number(e.target.value) })}
          />
          <p className="muted">24 fps is the first-run default (lighter encode). 30 fps is closer to the editor CSS preview. Android TV stays at H.264 1080p yuv420p.</p>
          <p className="muted">{describeMotion(style, intensity, duration)}. Intensity changes background amplitude only.</p>
          <div style={{ marginTop: 12 }}>
            <WallpaperStage
              wrapClassName="canvas-wrap generate-preview"
              artSrc={api.mediaArtwork("demo-jf-1")}
              artAlt="Motion intensity preview"
              motionOn
              motionVars={motionVars as CSSProperties}
              lightLeak={Boolean(settings.light_leak)}
            >
              <SampleLockedChrome title="Northlight" />
            </WallpaperStage>
          </div>
        </div>
        <div className="card">
          <h3>Overlay widgets</h3>
          <p className="muted">Off by default. Clock is a local demo widget; HA / news / JSON are documented hooks that render fixture cards so offline tests stay green.</p>
          <label>
            <input
              type="checkbox"
              checked={Boolean(settings.overlays_enabled)}
              onChange={(e) => setSettings({ ...settings, overlays_enabled: e.target.checked })}
            />{" "}
            Enable overlay widgets on generated stills / chrome
          </label>
          <label>
            <input
              type="checkbox"
              checked={Boolean(settings.overlay_clock)}
              onChange={(e) => setSettings({ ...settings, overlay_clock: e.target.checked })}
            />{" "}
            Clock card
          </label>
        </div>
        <div className="card">
          <h3>Title / logo</h3>
          <p className="muted">Default for new layouts. Each layout DNA JSON also stores <code>title_display</code> so Generate and the editor can prefer a clearlogo, always use the name, or auto-pick.</p>
          <label>Title display</label>
          <select
            value={settings.title_display || "auto"}
            aria-label="Default title display"
            onChange={(e) => setSettings({ ...settings, title_display: e.target.value as "auto" | "logo" | "text" })}
          >
            <option value="auto">Auto</option>
            <option value="logo">Prefer logo</option>
            <option value="text">Always title text</option>
          </select>
          <p className="muted">Auto uses the clearlogo when one was fetched, otherwise falls back to the title text.</p>
        </div>
        <div className="card">
          <h3>Editor appearance</h3>
          <label>Theme</label>
          <select
            value={settings.editor_theme || "cinema"}
            onChange={(e) => {
              setSettings({ ...settings, editor_theme: e.target.value });
              onTheme(e.target.value);
            }}
          >
            <option value="cinema">Cinema</option>
            <option value="midnight">Midnight</option>
            <option value="studio">Studio</option>
            <option value="high-contrast">High contrast</option>
          </select>
        </div>
        <div className="card">
          <h3>TMDB (optional enrichment)</h3>
          <p className="muted">Fills missing year / genres / runtime and clearlogos for Seerr titles (discover has no logos). Free key at themoviedb.org.</p>
          <label>API key</label>
          <input
            type="password"
            autoComplete="off"
            value={settings.tmdb.api_key || ""}
            onChange={(e) => patch("tmdb", "api_key", e.target.value)}
            placeholder="saved on the server"
          />
          <label>Language</label>
          <input value={settings.tmdb.language || "en-US"} onChange={(e) => patch("tmdb", "language", e.target.value)} />
          <button className="btn ghost tiny" style={{ marginTop: 10 }} onClick={() => testConnection("tmdb")}>Test TMDB</button>
        </div>
        <div className="card">
          <h3>OMDb (optional ratings)</h3>
          <p className="muted">Adds IMDb rating, Rotten Tomatoes, Metacritic, and awards to titles with a resolvable IMDb id (Jellyseerr's own detail lookup, no TMDB key needed). Free key at omdbapi.com. Add layers with these slots in the editor to show them.</p>
          <label>API key</label>
          <input
            type="password"
            autoComplete="off"
            value={settings.omdb.api_key || ""}
            onChange={(e) => patch("omdb", "api_key", e.target.value)}
            placeholder="saved on the server"
          />
        </div>
        <div className="card">
          <h3>Cron / batch</h3>
          <p className="muted">Each schedule runs independently on its own cron expression. A bad expression is rejected on Save (and skipped at boot) so a typo does not silently never run. Scheduled generate uses the same skip / replace / refresh-status / cleanup / id rules as the Generate page. Save settings to persist the schedules, or run one now for a toast with created / skipped / cleaned counts.</p>
          {(cronJobs.length ? cronJobs : [defaultCronJob("Schedule 1")]).map((cron, index) => (
            <div className="cron-job" key={index} style={{ borderTop: index > 0 ? "1px solid var(--line)" : undefined, marginTop: index > 0 ? 16 : 0, paddingTop: index > 0 ? 16 : 0 }}>
              <div className="row" style={{ justifyContent: "space-between", alignItems: "center" }}>
                <input
                  className="cron-job-name"
                  value={String(cron.name || "")}
                  onChange={(e) => setCronAt(index, { ...cron, name: e.target.value })}
                  placeholder={`Schedule ${index + 1}`}
                  aria-label={`Schedule ${index + 1} name`}
                />
                <button className="btn danger tiny" onClick={() => removeCronJob(index)}>
                  Delete schedule
                </button>
              </div>
              <label>
                <input
                  type="checkbox"
                  checked={Boolean(cron.enabled)}
                  onChange={(e) => setCronAt(index, { ...cron, enabled: e.target.checked })}
                />{" "}
                Enable scheduled generate
              </label>
              <label>Cron (5-field expression)</label>
              <input value={String(cron.cron || "")} onChange={(e) => setCronAt(index, { ...cron, cron: e.target.value })} placeholder="0 4 * * *" />
              <label>Layout</label>
              <select value={String(cron.layout || "Netflix Hero")} onChange={(e) => setCronAt(index, { ...cron, layout: e.target.value })} aria-label={`Schedule ${index + 1} layout`}>
                {(layouts.includes(String(cron.layout || "")) || !cron.layout ? layouts : [String(cron.layout), ...layouts]).map((name) => (
                  <option key={name}>{name}</option>
                ))}
                {layouts.length === 0 && <option>Netflix Hero</option>}
              </select>
              <label>Source</label>
              <select value={String(cron.source || "jellyfin")} onChange={(e) => setCronAt(index, { ...cron, source: e.target.value })}>
                <option value="demo">demo</option>
                <option value="jellyfin">jellyfin</option>
                <option value="jellyseerr">jellyseerr</option>
                <option value="all">all</option>
              </select>
              <label>Limit</label>
              <input
                type="number"
                min={1}
                max={200}
                value={Number(cron.limit || 20)}
                onChange={(e) => setCronAt(index, { ...cron, limit: Number(e.target.value) })}
              />
              <label>Only ids (comma)</label>
              <input
                value={Array.isArray(cron.ids) ? cron.ids.join(",") : String(cron.ids || "")}
                onChange={(e) => setCronAt(index, { ...cron, ids: csvToIds(e.target.value) })}
                placeholder="demo-jf-1, 90001"
              />
              <label>Skip ids (comma)</label>
              <input
                value={Array.isArray(cron.skip_ids) ? cron.skip_ids.join(",") : String(cron.skip_ids || "")}
                onChange={(e) => setCronAt(index, { ...cron, skip_ids: csvToIds(e.target.value) })}
                placeholder="leave blank to skip none extra"
              />

              <div className="cron-group">
                <p className="cron-group-label">Update behavior</p>
                <label>
                  <input
                    type="checkbox"
                    checked={Boolean(cron.replace_existing) && !cron.skip_existing}
                    onChange={(e) =>
                      setCronAt(
                        index,
                        e.target.checked
                          ? { ...cron, skip_existing: false, replace_existing: true }
                          : { ...cron, skip_existing: true, replace_existing: false },
                      )
                    }
                  />{" "}
                  Full refresh every run (re-fetch and replace everything, ignore skip)
                </label>
                <label>
                  <input
                    type="checkbox"
                    checked={Boolean(cron.skip_existing)}
                    disabled={Boolean(cron.replace_existing)}
                    onChange={(e) => setCronAt(index, { ...cron, skip_existing: e.target.checked })}
                  />{" "}
                  Skip existing by media id
                </label>
                <label>
                  <input
                    type="checkbox"
                    checked={Boolean(cron.replace_existing)}
                    onChange={(e) => setCronAt(index, { ...cron, replace_existing: e.target.checked, skip_existing: e.target.checked ? false : cron.skip_existing })}
                  />{" "}
                  Overwrite / replace
                </label>
                <label>
                  <input type="checkbox" checked={Boolean(cron.cleanup)} onChange={(e) => setCronAt(index, { ...cron, cleanup: e.target.checked })} />{" "}
                  Cleanup titles no longer in the source list
                </label>
              </div>

              <div className="cron-group">
                <p className="cron-group-label">Watch status</p>
                <label>
                  <input
                    type="checkbox"
                    checked={Boolean(cron.refresh_status)}
                    disabled={Boolean(cron.replace_existing)}
                    onChange={(e) => setCronAt(index, { ...cron, refresh_status: e.target.checked })}
                  />{" "}
                  Refresh when watch / availability changes
                </label>
              </div>

              {(cron.source === "jellyseerr" || cron.source === "all") && (
                <div className="cron-group">
                  <p className="cron-group-label">Seerr</p>
                  <label>Jellyseerr category</label>
                  <select value={String(cron.seerr_category || "trending")} onChange={(e) => setCronAt(index, { ...cron, seerr_category: e.target.value })}>
                    {SEERR_CATEGORIES.map((cat) => (
                      <option key={cat.id} value={cat.id}>{cat.label}</option>
                    ))}
                  </select>
                  {cron.cleanup && (
                    <p className="muted flag-help">
                      With cleanup on (above), every run deletes wallpapers for titles that fell out of this category — e.g. this fell out of Trending — so only what's currently trending/upcoming stays in the gallery.
                    </p>
                  )}
                </div>
              )}

              <div className="cron-group">
                <p className="cron-group-label">Motion</p>
                <label><input type="checkbox" checked={Boolean(cron.motion)} onChange={(e) => setCronAt(index, { ...cron, motion: e.target.checked })} /> Bake parallax VIDEO</label>
                <p className="muted flag-help">Uses the motion style/quality set above under Parallax / live motion.</p>
              </div>

              <p className="muted flag-help">
                {describeBatchFlags({
                  skip_existing: Boolean(cron.skip_existing),
                  replace_existing: Boolean(cron.replace_existing),
                  refresh_status: Boolean(cron.refresh_status),
                  cleanup: Boolean(cron.cleanup),
                  ids: Array.isArray(cron.ids) ? cron.ids : csvToIds(String(cron.ids || "")),
                  skip_ids: Array.isArray(cron.skip_ids) ? cron.skip_ids : csvToIds(String(cron.skip_ids || "")),
                })}
              </p>
              <button
                className="btn tiny"
                style={{ marginTop: 12 }}
                disabled={busy}
                onClick={async () => {
                  try {
                    const out = await run({
                      kind: "cron",
                      layout: cron.layout,
                      source: cron.source,
                      seerr_category: cron.seerr_category,
                      limit: Math.min(200, Math.max(1, Number(cron.limit) || 20)),
                      skip_existing: cron.skip_existing,
                      replace_existing: cron.replace_existing,
                      refresh_status: cron.refresh_status,
                      cleanup: cron.cleanup,
                      motion: cron.motion,
                      ids: Array.isArray(cron.ids) ? cron.ids : csvToIds(String(cron.ids || "")),
                      skip_ids: Array.isArray(cron.skip_ids) ? cron.skip_ids : csvToIds(String(cron.skip_ids || "")),
                    });
                    setMsg(out.message || String((out.result as { message?: string } | null)?.message || ""));
                  } catch (err) {
                    setMsg(errorToast(err, "Cron run failed").text);
                  }
                }}
              >
                Run now
              </button>
            </div>
          ))}
          <div className="row" style={{ marginTop: 16 }}>
            <button className="btn ghost tiny" onClick={() => addCronJob()}>
              Add cron job
            </button>
          </div>
        </div>
        </>
        )}
      </div>
      <button
        className="btn"
        style={{ marginTop: 18 }}
        onClick={async () => {
          try {
            await api.saveSettings(settings);
            setMsg("Saved settings");
            notify("ok", "Saved settings");
            onTheme(settings.editor_theme || "cinema");
          } catch (err) {
            const toast = errorToast(err, "Could not save settings");
            notify(toast.kind, toast.text);
            setMsg(toast.text);
          }
        }}
      >
        Save settings
      </button>
      {msg && <p className="status">{msg}</p>}
    </section>
  );
}
