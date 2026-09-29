// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Ruan Pato

import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import type { Task, Overview, Snapshot, Tokens, Window } from "./types";
import {
  compact,
  formatNumber as num,
  money,
  duration,
  deltaLabel,
  matchesSearch,
  formatDateTime,
} from "./types";
import "./style.css";
import { t as tr, getLocale, setPreferredLocale, type Locale } from "./i18n";
const pages = [
  "Overview",
  "Tasks",
  "Sessions",
  "Projects",
  "Quota",
  "Integrations",
  "Settings",
];
const paths = [
  "M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z",
  "M5 5h14M5 12h14M5 19h14",
  "M4 6h16v12H4z M8 22h8 M12 18v4",
  "M3 7h7l2 3h9v10H3z",
  "M3 17a9 9 0 1 1 18 0 M12 16l5-6",
  "M8 3v6 M16 3v6 M5 9h14v4a7 7 0 0 1-14 0z M12 20v3",
  "M12 8a4 4 0 1 0 0 8a4 4 0 0 0 0-8 M12 2v3 M12 19v3 M2 12h3 M19 12h3 M5 5l2 2 M17 17l2 2 M5 19l2-2 M17 7l2-2",
];
function Icon({ index, size = 20 }: { index: number; size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d={paths[index]} />
    </svg>
  );
}
async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch("/api" + path, init);
  if (!r.ok) {
    const data = await r.json().catch(() => ({ detail: r.statusText }));
    throw new Error(
      typeof data.detail === "string"
        ? tr(data.detail)
        : tr("Check the entered values and try again."),
    );
  }
  return r.json();
}
function Badge({
  children,
  tone = "neutral",
}: {
  children: React.ReactNode;
  tone?: string;
}) {
  return <span className={"badge " + tone}>{children}</span>;
}
function App() {
  const [locale, setLocale] = useState<Locale>(getLocale);
  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);
  const [page, setPage] = useState("Overview"),
    [mode, setMode] = useState(
      localStorage.getItem("tracequota-mode") || "all",
    );
  const [overview, setOverview] = useState<Overview | null>(null),
    [tasks, setTasks] = useState<Task[]>([]),
    [selected, setSelected] = useState<Task | null>(null),
    [quota, setQuota] = useState<Snapshot[]>([]);
  const [extra, setExtra] = useState<any>(null),
    [settings, setSettings] = useState<any>(null),
    [error, setError] = useState(""),
    [loading, setLoading] = useState(true),
    [search, setSearch] = useState(""),
    [status, setStatus] = useState(""),
    [sort, setSort] = useState("started_at"),
    [since, setSince] = useState("");
  const [filters, setFilters] = useState<Record<string, string>>({});
  const [options, setOptions] = useState<Record<string, string[]>>({});
  const requestVersion = useRef(0);
  const params = new URLSearchParams();
  if (mode !== "all") params.set("demo", String(mode === "demo"));
  Object.entries(filters).forEach(([key, value]) => {
    if (value) params.set(key, value);
  });
  if (since) params.set("since", since);
  const query = params.toString();
  async function load() {
    const version = ++requestVersion.current;
    try {
      const [o, t, q, s, e, f] = await Promise.all([
        api<Overview>("/overview?" + query),
        api<Task[]>(
          `/tasks?${query}&sort=${sort}${status ? "&status=" + status : ""}&limit=1000`,
        ),
        api<Snapshot[]>("/quota?" + query),
        api("/settings"),
        api(
          "/" +
            (page === "Sessions"
              ? "sessions"
              : page === "Projects"
                ? "projects"
                : "integrations") +
            "?" +
            query,
        ),
        api<Record<string, string[]>>("/filters"),
      ]);
      if (version !== requestVersion.current) return;
      setOptions(f);
      setOverview(o);
      setTasks(t);
      setQuota(q);
      setSettings(s);
      setExtra(e);
      setError("");
    } catch (e) {
      if (version === requestVersion.current) setError(String(e));
    } finally {
      if (version === requestVersion.current) setLoading(false);
    }
  }
  useEffect(() => {
    setLoading(true);
    void load();
    const id = setInterval(() => void load(), 15000);
    return () => {
      clearInterval(id);
      requestVersion.current++;
    };
  }, [page, mode, status, sort, since, query]);
  async function openTask(t: Task) {
    try {
      setSelected(await api<Task>("/tasks/" + encodeURIComponent(t.id)));
    } catch (e) {
      setError(String(e));
    }
  }
  const links = settings?.links || {
    grafana: "http://localhost:3000",
    phoenix: "http://localhost:6006",
  };
  const filtered = tasks.filter((t) => matchesSearch(t, search));
  const date = new Intl.DateTimeFormat(locale, {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(new Date());
  return (
    <div className="app">
      <aside>
        <a className="brand" href="#" onClick={() => setPage("Overview")}>
          <span className="brand-mark">↗</span>
          <span>
            TraceQuota<small>{tr("AGENT OBSERVABILITY")}</small>
          </span>
        </a>
        <div className="workspace-label">{tr("YOUR WORKSPACE")}</div>
        <nav>
          {pages.map((p, i) => (
            <button
              key={p}
              className={p === page ? "active" : ""}
              onClick={() => {
                setPage(p);
                setSelected(null);
              }}
            >
              <Icon index={i} />
              {tr(p)}
              {p === "Tasks" && (
                <span className="nav-count">{tasks.length}</span>
              )}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="local">
            <span className="dot" />
            {tr("Local-first by design")}
          </div>
          <p>
            {tr("Your telemetry stays")}
            <br />
            {tr("on your machine.")}
          </p>
          <div className="sidebar-version">
            {tr("OPEN SOURCE")} <span>v0.2.0</span>
          </div>
        </div>
      </aside>
      <div className="shell">
        <header>
          <div className="breadcrumb">
            {tr("Workspace")} <span>/</span> <b>{tr(page)}</b>
          </div>
          <div className="header-right">
            <select
              aria-label={tr("Language")}
              value={locale}
              onChange={(e) => {
                const next = e.target.value as Locale;
                setPreferredLocale(next);
                setLocale(next);
              }}
            >
              <option value="en-US">English (US)</option>
              <option value="pt-BR">Português (Brasil)</option>
            </select>
            <span className="date">{date}</span>
            <select
              aria-label={tr("Data source")}
              value={mode}
              onChange={(e) => {
                setMode(e.target.value);
                localStorage.setItem("tracequota-mode", e.target.value);
              }}
            >
              <option value="all">{tr("All local data")}</option>
              <option value="live">{tr("Live data")}</option>
              <option value="demo">{tr("Demo data")}</option>
            </select>
            <span className="avatar">L</span>
          </div>
        </header>
        <main>
          <div className="page-heading">
            <div>
              <div className="eyebrow">
                {page === "Overview"
                  ? tr("YOUR AGENTS, IN FOCUS")
                  : tr("LOCAL OBSERVABILITY")}
              </div>
              <h1>
                {page === "Overview"
                  ? tr("Know where your context goes.")
                  : tr(page)}
              </h1>
              <p>
                {page === "Overview"
                  ? tr(
                      "A clear view of agent usage, task costs, and quota. All in one place.",
                    )
                  : page === "Tasks"
                    ? tr("Follow the work. Understand the resource footprint.")
                    : page === "Quota"
                      ? tr(
                          "Subscription windows, with a source behind every number.",
                        )
                      : tr("Explore the activity in your local workspace.")}
              </p>
            </div>
            <div className="actions">
              <a
                href={links.grafana + "/d/tracequota/tracequota"}
                target="_blank"
                rel="noreferrer"
                className="button"
              >
                {tr("Grafana ↗")}
              </a>
              <a
                href={links.phoenix}
                target="_blank"
                rel="noreferrer"
                className="button dark"
              >
                {tr("Open Phoenix ↗")}
              </a>
            </div>
          </div>
          {tasks.some((t) => t.demo) && mode !== "live" && (
            <div className="demo-banner">
              <span>◈</span>
              <b>{tr("Synthetic demo data")}</b>
              <span>
                {tr(
                  "Demonstration activity is labeled throughout your workspace.",
                )}
              </span>
              <button
                onClick={() => {
                  setMode("live");
                  localStorage.setItem("tracequota-mode", "live");
                }}
              >
                {tr("View live data →")}
              </button>
            </div>
          )}
          {["Overview", "Tasks", "Sessions", "Projects"].includes(page) && (
            <details className="card dimension-filters">
              <summary>
                {tr("Filter usage")}{" "}
                {Object.values(filters).filter(Boolean).length > 0 && (
                  <Badge>
                    {Object.values(filters).filter(Boolean).length}{" "}
                    {tr("active")}
                  </Badge>
                )}
              </summary>
              <div className="dimension-grid">
                {[
                  "client",
                  "surface",
                  "runtime",
                  "integration_type",
                  "provider",
                  "billing_platform",
                  "model",
                  "project",
                  "repository",
                  "agent",
                  "pricing_confidence",
                ].map((key) => (
                  <label key={key}>
                    {tr(key.replaceAll("_", " "))}
                    <select
                      aria-label={tr(key.replaceAll("_", " "))}
                      value={filters[key] || ""}
                      onChange={(e) =>
                        setFilters({ ...filters, [key]: e.target.value })
                      }
                    >
                      <option value="">{tr("All")}</option>
                      {(options[key] || []).map((value) => (
                        <option key={value} value={value}>
                          {value}
                        </option>
                      ))}
                    </select>
                  </label>
                ))}
                <label>
                  {tr("From")}
                  <input
                    type="datetime-local"
                    aria-label={tr("From date filter")}
                    value={filters.since || ""}
                    onChange={(e) =>
                      setFilters({ ...filters, since: e.target.value })
                    }
                  />
                </label>
                <label>
                  {tr("Through")}
                  <input
                    type="datetime-local"
                    aria-label={tr("Through date filter")}
                    value={filters.until || ""}
                    onChange={(e) =>
                      setFilters({ ...filters, until: e.target.value })
                    }
                  />
                </label>
                <button
                  className="button"
                  onClick={() => {
                    setFilters({});
                    setSince("");
                  }}
                >
                  {tr("Clear filters")}
                </button>
              </div>
            </details>
          )}
          {error && (
            <div className="error" role="alert">
              {error}
              <button onClick={() => void load()}>{tr("Retry")}</button>
            </div>
          )}
          {loading && !overview ? (
            <div className="empty">
              {tr("Connecting to your local ledger…")}
            </div>
          ) : (
            <>
              {page === "Overview" && overview && (
                <>
                  <div className="stat-grid">
                    <Stat
                      label={tr("Token activity today")}
                      value={compact(overview.tokens_today)}
                      hint={tr("Known input + output + cache · UTC")}
                      icon="↗"
                    />
                    <Stat
                      label={tr("Token activity this week")}
                      value={compact(overview.tokens_week)}
                      hint={tr("Week starts Monday · UTC")}
                      icon="◴"
                    />
                    <Stat
                      label={tr("Tasks today")}
                      value={num(overview.tasks_today)}
                      hint={tr("Explicit tasks & interactions")}
                      icon="≡"
                    />
                    <Stat
                      label={tr("Observed sessions")}
                      value={num(overview.sessions)}
                      hint={tr("{count} projects in your ledger", {
                        count: overview.projects,
                      })}
                      icon="▣"
                    />
                  </div>
                  <CostOverview overview={overview} />
                  <div className="overview-grid">
                    <section className="card usage-card">
                      <CardTitle
                        title={tr("Where the tokens go")}
                        detail={tr("Calculated from observed requests")}
                      />
                      <div className="token-viz">
                        {Object.entries(overview.models).length ? (
                          <>
                            <div className="viz-number">
                              {compact(
                                tasks.reduce(
                                  (s, t) => s + t.total_token_activity,
                                  0,
                                ),
                              )}
                              <span>{tr("total token activity")}</span>
                            </div>
                            <div className="stacked-bar">
                              {[
                                "input",
                                "output",
                                "cache_read",
                                "cache_write",
                              ].map((k, i) => {
                                const n = tasks.reduce(
                                    (s, t) => s + t.tokens[k as keyof Tokens],
                                    0,
                                  ),
                                  total = tasks.reduce(
                                    (s, t) => s + t.total_token_activity,
                                    0,
                                  );
                                return (
                                  <span
                                    key={k}
                                    style={{
                                      width: `${total ? (n / total) * 100 : 0}%`,
                                      background: [
                                        "#7776e7",
                                        "#45a993",
                                        "#b7b7ef",
                                        "#e3b86d",
                                      ][i],
                                    }}
                                    title={`${tr(k.replaceAll("_", " "))}: ${num(n)}`}
                                  />
                                );
                              })}
                            </div>
                            <div className="token-legend">
                              {[
                                "Input",
                                "Output",
                                "Cache read",
                                "Cache write",
                              ].map((label, i) => (
                                <div key={label}>
                                  <i
                                    style={{
                                      background: [
                                        "#7776e7",
                                        "#45a993",
                                        "#b7b7ef",
                                        "#e3b86d",
                                      ][i],
                                    }}
                                  />
                                  {tr(label)}
                                  <b>
                                    {compact(
                                      tasks.reduce(
                                        (s, t) =>
                                          s +
                                          t.tokens[
                                            [
                                              "input",
                                              "output",
                                              "cache_read",
                                              "cache_write",
                                            ][i] as keyof Tokens
                                          ],
                                        0,
                                      ),
                                    )}
                                  </b>
                                </div>
                              ))}
                            </div>
                          </>
                        ) : (
                          <Empty />
                        )}
                      </div>
                      <p className="footnote">
                        {tr(
                          "Cache reads represent reused context. API-equivalent cost is an estimate.",
                        )}
                      </p>
                    </section>
                    <section className="card">
                      <CardTitle
                        title={tr("Last-known provider quota")}
                        detail={tr("Snapshot evidence")}
                        action={() => setPage("Quota")}
                      />
                      <QuotaCards snapshots={quota} compactMode />
                    </section>
                  </div>
                  <div className="breakdown-grid">
                    <Breakdown title={tr("By model")} data={overview.models} />
                    <Breakdown title={tr("By agent")} data={overview.agents} />
                    <Breakdown
                      title={tr("By project")}
                      data={overview.project_usage}
                    />
                  </div>
                  <section className="card">
                    <CardTitle
                      title={tr("Recent work")}
                      detail={tr("Your latest tasks and interactions")}
                      action={() => setPage("Tasks")}
                    />
                    <TaskTable tasks={overview.tasks} onSelect={openTask} />
                  </section>
                </>
              )}
              {page === "Tasks" && (
                <section className="card">
                  <div className="table-controls">
                    <input
                      aria-label={tr("Search tasks")}
                      placeholder={tr("Search projects, models, agents…")}
                      value={search}
                      onChange={(e) => setSearch(e.target.value)}
                    />
                    <select
                      aria-label={tr("Task status")}
                      value={status}
                      onChange={(e) => setStatus(e.target.value)}
                    >
                      <option value="">{tr("All statuses")}</option>
                      <option value="completed">{tr("Completed")}</option>
                      <option value="failed">{tr("Failed")}</option>
                      <option value="running">{tr("Running")}</option>
                    </select>
                    <input
                      type="date"
                      aria-label={tr("Tasks since")}
                      value={since}
                      onChange={(e) => setSince(e.target.value)}
                    />
                    <select
                      aria-label={tr("Sort tasks")}
                      value={sort}
                      onChange={(e) => setSort(e.target.value)}
                    >
                      {[
                        ["started_at", "Latest first"],
                        ["project", "Project"],
                        ["total_token_activity", "Most tokens"],
                        ["estimated_api_cost", "Highest cost"],
                        ["duration_seconds", "Longest duration"],
                        ["quota_delta_pp", "Largest quota delta"],
                      ].map(([v, l]) => (
                        <option value={v} key={v}>
                          {l}
                        </option>
                      ))}
                    </select>
                  </div>
                  <TaskTable tasks={filtered} onSelect={openTask} />
                </section>
              )}
              {page === "Quota" && (
                <>
                  <QuotaCards snapshots={quota} />
                  <div className="overview-grid">
                    <QuotaForm onSaved={() => void load()} />
                    <section className="card note">
                      <h2>{tr("Evidence, before estimates.")}</h2>
                      <p>
                        {tr(
                          "Official snapshots come from Claude’s documented status-line payload. Manual snapshots are entered by you. Estimated quota uses an explicit capacity you provide.",
                        )}
                      </p>
                      <p>
                        {tr("A task’s delta is measured in")}{" "}
                        <b>{tr("percentage points")}</b>
                        {tr(
                          ". A reset crossing has no single delta. Other sessions can contribute to account-wide changes.",
                        )}
                      </p>
                      <Badge tone="purple">
                        {tr("No credential scraping")}
                      </Badge>
                    </section>
                  </div>
                  <section className="card">
                    <CardTitle
                      title={tr("Snapshot history")}
                      detail={tr("Capture time · UTC")}
                    />
                    <div className="table-scroll">
                      <table>
                        <thead>
                          <tr>
                            <th>{tr("Captured")}</th>
                            <th>{tr("Account")}</th>
                            <th>{tr("Source")}</th>
                            <th>{tr("Windows")}</th>
                          </tr>
                        </thead>
                        <tbody>
                          {quota.map((q) => (
                            <tr key={q.id}>
                              <td>{formatDateTime(q.captured_at)}</td>
                              <td>
                                {q.provider} / {q.account}
                                {q.demo && <Badge>{tr("demo")}</Badge>}
                              </td>
                              <td>
                                <Badge tone="purple">
                                  {tr(q.source.replaceAll("_", " "))}
                                </Badge>
                              </td>
                              <td>
                                {q.windows
                                  .map(
                                    (w) =>
                                      `${tr(w.name)}: ${num(w.used_percent)}%`,
                                  )
                                  .join(" · ")}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    {!quota.length && <Empty />}
                  </section>
                </>
              )}
              {(page === "Sessions" || page === "Projects") &&
                Array.isArray(extra) && (
                  <section className="card">
                    <CardTitle
                      title={tr(page)}
                      detail={tr("Usage from your request ledger")}
                    />
                    <div className="table-scroll">
                      <table>
                        <thead>
                          <tr>
                            <th>
                              {page === "Sessions"
                                ? tr("Session")
                                : tr("Project")}
                            </th>
                            <th>{tr("Tasks")}</th>
                            <th>{tr("Token activity")}</th>
                            <th>{tr("Details")}</th>
                          </tr>
                        </thead>
                        <tbody>
                          {extra
                            .filter(
                              (r: any) =>
                                page === "Projects" ||
                                mode === "all" ||
                                r.demo === (mode === "demo"),
                            )
                            .map((r: any) => (
                              <tr key={r.id || r.name}>
                                <td>
                                  <b>{r.name || r.id}</b>
                                  <small>
                                    {r.client_id || tr("Project")}
                                    {r.providers?.length
                                      ? ` · ${r.providers.join(", ")}`
                                      : ""}
                                  </small>
                                </td>
                                <td>
                                  {r.tasks}
                                  <small>
                                    {money(r.estimated_api_equivalent_cost)}{" "}
                                    {tr("API equivalent")}
                                  </small>
                                </td>
                                <td>{num(r.tokens)}</td>
                                <td>
                                  {r.project || tr("Local project")}{" "}
                                  {r.demo && <Badge>{tr("demo")}</Badge>}
                                  <button
                                    className="text-button"
                                    onClick={() => {
                                      setSearch(r.name || r.id);
                                      setPage("Tasks");
                                    }}
                                  >
                                    {tr("View tasks →")}
                                  </button>
                                </td>
                              </tr>
                            ))}
                        </tbody>
                      </table>
                    </div>
                    {!extra.length && <Empty />}
                  </section>
                )}
              {page === "Integrations" && extra && (
                <div className="integration-grid">
                  {(extra.clients || []).map((client: any) => (
                    <section className="card integration" key={client.id}>
                      <span className="integration-icon">
                        <Icon index={5} size={28} />
                      </span>
                      <h2>{client.name}</h2>
                      <p>{tr(client.integration_type.replaceAll("_", " "))}</p>
                      <Badge tone={client.last_seen ? "green" : "neutral"}>
                        {client.last_seen
                          ? tr("Telemetry received")
                          : client.validation === "planned"
                            ? tr("Planned")
                            : tr("Awaiting telemetry")}
                      </Badge>
                      <p className="footnote">
                        {tr("Validation:")}{" "}
                        {tr(client.validation.replaceAll("_", " "))}
                        {client.demo_seen && tr(" · synthetic data received")}
                      </p>
                      <dl>
                        {Object.entries(client.capabilities).map(
                          ([name, capability]) => (
                            <React.Fragment key={name}>
                              <dt>{tr(name.replaceAll("_", " "))}</dt>
                              <dd>
                                {tr(String(capability).replaceAll("_", " "))}
                              </dd>
                            </React.Fragment>
                          ),
                        )}
                      </dl>
                      {client.id === "cursor" && (
                        <p className="footnote">
                          {tr(
                            "Session metadata only. Tokens, costs and quota are unavailable from Cursor hooks.",
                          )}
                        </p>
                      )}
                      {client.validation !== "planned" && (
                        <IntegrationPrompt client={client} />
                      )}
                      {client.source && (
                        <a
                          href={client.source}
                          target="_blank"
                          rel="noreferrer"
                        >
                          {tr("Official documentation ↗")}
                        </a>
                      )}
                    </section>
                  ))}
                  <section className="card integration">
                    <h2>{tr("Connect Claude Code")}</h2>
                    <p>
                      {tr(
                        "Start the stack, configure the CLI or Desktop Local environment, and run Claude normally. Your agent stays on the host.",
                      )}
                    </p>
                    <pre>
                      CLAUDE_CODE_ENABLE_TELEMETRY=1
                      <br />
                      OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
                      <br />
                      OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
                    </pre>
                    <p>
                      {tr(
                        "See the repository onboarding guide for complete shell and PowerShell settings, hooks, and the quota adapter.",
                      )}
                    </p>
                  </section>
                </div>
              )}
              {page === "Settings" && settings && (
                <div className="overview-grid">
                  <PricingSettings
                    status={settings.pricing}
                    onSynced={() => void load()}
                  />
                  <section className="card note">
                    <h2>{tr("Privacy comes standard.")}</h2>
                    <dl>
                      <dt>{tr("Capture mode")}</dt>
                      <dd>{tr(settings.privacy_mode)}</dd>
                      <dt>{tr("Storage")}</dt>
                      <dd>{tr("Local named Docker volumes")}</dd>
                      <dt>{tr("Account")}</dt>
                      <dd>{tr("No TraceQuota account required")}</dd>
                      <dt>{tr("Retention")}</dt>
                      <dd>{tr(settings.retention)}</dd>
                      <dt>{tr("Pricing table")}</dt>
                      <dd>{settings.pricing_version}</dd>
                      <dt>{tr("Time calculations")}</dt>
                      <dd>UTC</dd>
                    </dl>
                    <p>
                      {tr(
                        "Prompts, responses, source content, shell output and credentials are removed from the default pipeline.",
                      )}
                    </p>
                  </section>
                  <section className="card note">
                    <h2>{tr("Tools for investigation")}</h2>
                    <p>
                      {tr(
                        "Use Phoenix for execution trees and Grafana for time series. TraceQuota connects them to your local task and quota ledger.",
                      )}
                    </p>
                    <a
                      className="button"
                      href={links.phoenix}
                      target="_blank"
                      rel="noreferrer"
                    >
                      {tr("Open Phoenix ↗")}
                    </a>
                    <a
                      className="button"
                      href={links.grafana}
                      target="_blank"
                      rel="noreferrer"
                    >
                      {tr("Open Grafana ↗")}
                    </a>
                    <h3>{tr("Rich capture")}</h3>
                    <p>
                      {tr(
                        "Requires an explicit custom Collector configuration. There is no one-click switch that could accidentally retain private content.",
                      )}
                    </p>
                  </section>
                </div>
              )}
            </>
          )}
          <footer>
            <span>
              <span className="dot" />
              {tr("All data stored locally")}
            </span>
            <span>{tr("TraceQuota · Metadata with meaning.")}</span>
          </footer>
        </main>
      </div>
      {selected && (
        <TaskDetail
          task={selected}
          onClose={() => setSelected(null)}
          phoenix={links.phoenix}
        />
      )}
    </div>
  );
}
function Stat({
  label,
  value,
  hint,
  icon,
}: {
  label: string;
  value: string;
  hint: string;
  icon: string;
}) {
  return (
    <section className="card stat">
      <div>
        {label}
        <span>{icon}</span>
      </div>
      <strong>{value}</strong>
      <p>{hint}</p>
    </section>
  );
}
function CardTitle({
  title,
  detail,
  action,
}: {
  title: string;
  detail?: string;
  action?: () => void;
}) {
  return (
    <div className="card-heading">
      <div>
        <h2>{title}</h2>
        {detail && <p>{detail}</p>}
      </div>
      {action && (
        <button onClick={action} className="text-button">
          {tr("View all →")}
        </button>
      )}
    </div>
  );
}
function Empty() {
  return (
    <div className="empty">
      <strong>{tr("Your ledger is ready.")}</strong>
      <p>{tr("Run the demo or connect an agent to see activity here.")}</p>
      <code>docker compose run --rm tracequota-demo</code>
    </div>
  );
}
function Breakdown({
  title,
  data,
}: {
  title: string;
  data: Record<string, number>;
}) {
  const values = Object.entries(data).slice(0, 4),
    max = Math.max(...values.map(([, v]) => v), 1);
  return (
    <section className="card breakdown">
      <CardTitle title={title} detail={tr("Token activity")} />
      {values.length ? (
        values.map(([name, n], i) => (
          <div className="breakdown-row" key={name}>
            <div>
              <span
                className="list-dot"
                style={{
                  background: ["#7776e7", "#45a993", "#dda75b", "#8799b1"][i],
                }}
              />
              <span title={name}>{name}</span>
              <b>{compact(n)}</b>
            </div>
            <div className="mini-track">
              <span style={{ width: `${(n / max) * 100}%` }} />
            </div>
          </div>
        ))
      ) : (
        <p className="muted">{tr("No observations yet.")}</p>
      )}
    </section>
  );
}
function QuotaCards({
  snapshots,
  compactMode = false,
}: {
  snapshots: Snapshot[];
  compactMode?: boolean;
}) {
  const [account, setAccount] = useState("");
  const groups = Array.from(
    new Set(
      snapshots.map(
        (q) => `${q.provider}/${q.account}/${q.demo ? "demo" : "live"}`,
      ),
    ),
  );
  const chosen = groups.includes(account) ? account : groups[0];
  const current = snapshots.find(
    (q) => `${q.provider}/${q.account}/${q.demo ? "demo" : "live"}` === chosen,
  );
  return (
    <div className={compactMode ? "quota-compact" : "quota-grid"}>
      {groups.length > 1 && (
        <select
          className="account-picker"
          aria-label={tr("Quota account")}
          value={chosen}
          onChange={(e) => setAccount(e.target.value)}
        >
          {groups.map((g) => (
            <option key={g}>{g}</option>
          ))}
        </select>
      )}
      {current ? (
        current.windows.map((w) => (
          <QuotaWindow
            key={tr(w.name)}
            window={w}
            snapshot={current}
            compactMode={compactMode}
          />
        ))
      ) : (
        <div className="empty">
          <p>{tr("No quota snapshot yet.")}</p>
          <span>
            {tr("Record a manual snapshot or connect the status-line adapter.")}
          </span>
        </div>
      )}
    </div>
  );
}
function QuotaWindow({
  window: w,
  snapshot: q,
  compactMode,
}: {
  window: Window;
  snapshot: Snapshot;
  compactMode: boolean;
}) {
  return (
    <section className={compactMode ? "quota-window" : "card quota-window"}>
      <div className="quota-label">
        <b>
          {q.provider === "anthropic" ? tr("Claude") : q.provider} {tr(w.name)}
        </b>
        <Badge tone="purple">
          {tr(q.source.replaceAll("_", " "))}
          {q.demo ? tr(" · demo") : ""}
        </Badge>
      </div>
      <div className="quota-value">
        <strong>{num(w.used_percent)}%</strong>
        <span>
          {tr("used")}{" "}
          <b>
            {num(Math.round(w.remaining_percent * 10) / 10)}
            {tr("% remaining")}
          </b>
        </span>
      </div>
      <div className="quota-track">
        <span
          style={{ width: `${num(w.used_percent)}%` }}
          className={w.used_percent > 80 ? "high" : ""}
        />
      </div>
      <p className="footnote">
        {w.reset_at
          ? tr("Resets {date}", { date: formatDateTime(w.reset_at) })
          : tr("Reset time not supplied")}
        <br />
        {tr("Captured")} {formatDateTime(q.captured_at)}
      </p>
    </section>
  );
}
function TaskTable({
  tasks,
  onSelect,
}: {
  tasks: Task[];
  onSelect: (t: Task) => void;
}) {
  return (
    <>
      {tasks.length ? (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>{tr("Task / project")}</th>
                <th>{tr("Agent / model")}</th>
                <th>{tr("Token activity")}</th>
                <th>{tr("API equivalent")}</th>
                <th>{tr("Duration")}</th>
                <th>{tr("5h quota")}</th>
                <th>{tr("Status")}</th>
              </tr>
            </thead>
            <tbody>
              {tasks.map((t) => (
                <tr key={t.id} onClick={() => onSelect(t)}>
                  <td>
                    <button
                      className="task-link"
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelect(t);
                      }}
                    >
                      {t.title} <span>↗</span>
                    </button>
                    <small>
                      {t.project} · {t.client_id}{" "}
                      {t.demo && <Badge>{tr("demo")}</Badge>}
                    </small>
                  </td>
                  <td>
                    {Object.keys(t.agents).slice(0, 2).join(" + ") ||
                      "No requests"}
                    <small>{Object.keys(t.models)[0] || "—"}</small>
                  </td>
                  <td className="mono">{num(t.total_token_activity)}</td>
                  <td className="mono">
                    {money(t.estimated_api_cost)}
                    <small>
                      {t.unpriced_requests
                        ? tr("{cost} priced · {count} incomplete", {
                            cost: money(t.priced_partial_cost),
                            count: t.unpriced_requests,
                          })
                        : tr("API equivalent")}
                    </small>
                  </td>
                  <td>{duration(t.duration_seconds)}</td>
                  <td>
                    <span className="quota-delta">
                      {deltaLabel(t.quota_delta.find((d) => d.name === "5h"))}
                    </span>
                  </td>
                  <td>
                    <Badge
                      tone={
                        t.status === "completed"
                          ? "green"
                          : t.status === "failed"
                            ? "red"
                            : "purple"
                      }
                    >
                      <span className="tiny-dot" />
                      {tr(t.status)}
                    </Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <Empty />
      )}
    </>
  );
}
function QuotaForm({ onSaved }: { onSaved: () => void }) {
  const [used, setUsed] = useState(""),
    [weekly, setWeekly] = useState(""),
    [reset, setReset] = useState(""),
    [account, setAccount] = useState("default"),
    [provider, setProvider] = useState("anthropic"),
    [source, setSource] = useState("manual"),
    [capacity, setCapacity] = useState(""),
    [notice, setNotice] = useState(""),
    [saving, setSaving] = useState(false);
  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    try {
      if (source === "estimated") {
        await api("/quota/estimate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            account,
            provider,
            used_units: Number(used),
            capacity: Number(capacity),
          }),
        });
      } else {
        const windows: any[] = [
          {
            name: "5h",
            type: "rolling",
            used_percent: Number(used),
            reset_at: reset ? new Date(reset).toISOString() : null,
          },
        ];
        if (weekly)
          windows.push({
            name: "weekly",
            type: "weekly",
            used_percent: Number(weekly),
          });
        await api("/quota/snapshots", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            provider,
            account,
            source,
            windows,
          }),
        });
      }
      setNotice(tr("Snapshot saved locally."));
      onSaved();
    } catch (e) {
      setNotice(String(e));
    } finally {
      setSaving(false);
    }
  }
  return (
    <form className="card quota-form" onSubmit={submit}>
      <h2>{tr("Record a snapshot")}</h2>
      <p>
        {tr("Enter the quota shown by your provider, or an explicit estimate.")}
      </p>
      <div className="form-grid">
        <label>
          {tr("Provider")}
          <input
            aria-label={tr("Quota provider")}
            value={provider}
            onChange={(e) => setProvider(e.target.value)}
            maxLength={80}
            required
          />
        </label>
        <label>
          {tr("Account")}
          <input
            value={account}
            onChange={(e) => setAccount(e.target.value)}
            required
          />
        </label>
        <label>
          {tr("Evidence source")}
          <select value={source} onChange={(e) => setSource(e.target.value)}>
            <option value="manual">{tr("Manual")}</option>
            <option value="estimated">{tr("Estimated")}</option>
          </select>
        </label>
        <label>
          {source === "manual" ? tr("5h used (%)") : tr("Used units")}
          <input
            type="number"
            min="0"
            max={source === "manual" ? 100 : undefined}
            step="any"
            value={used}
            onChange={(e) => setUsed(e.target.value)}
            required
          />
        </label>
        {source === "manual" ? (
          <label>
            {tr("Weekly used (%) · optional")}
            <input
              type="number"
              min="0"
              max="100"
              step="any"
              value={weekly}
              onChange={(e) => setWeekly(e.target.value)}
            />
          </label>
        ) : (
          <label>
            {tr("Your assumed capacity")}
            <input
              type="number"
              min="0.001"
              step="any"
              value={capacity}
              onChange={(e) => setCapacity(e.target.value)}
              required
            />
          </label>
        )}
        {source === "manual" && (
          <label className="full">
            {tr("5h reset · optional")}
            <input
              type="datetime-local"
              value={reset}
              onChange={(e) => setReset(e.target.value)}
            />
          </label>
        )}
      </div>
      <button className="button dark" disabled={saving}>
        {saving ? tr("Saving…") : tr("Save snapshot")}
      </button>
      {notice && <p role="status">{notice}</p>}
    </form>
  );
}
function TaskDetail({
  task: t,
  onClose,
  phoenix,
}: {
  task: Task;
  onClose: () => void;
  phoenix: string;
}) {
  useEffect(() => {
    function key(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", key);
    return () => document.removeEventListener("keydown", key);
  }, [onClose]);
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <section
        className="detail"
        role="dialog"
        aria-modal="true"
        aria-label={tr("Task detail")}
        onClick={(e) => e.stopPropagation()}
      >
        <button
          className="close"
          onClick={onClose}
          aria-label={tr("Close task detail")}
        >
          ×
        </button>
        <div className="eyebrow">
          {tr("TASK INVESTIGATION")} {t.demo && tr("· SYNTHETIC DEMO")}
        </div>
        <h1>{t.title}</h1>
        <p>
          {t.project}{" "}
          <span className="muted">/ {tr(t.kind.replaceAll("_", " "))}</span>
        </p>
        <Badge tone={t.status === "failed" ? "red" : "green"}>
          {tr(t.status)}
        </Badge>
        <div className="detail-stats">
          <Stat
            label={tr("Known token activity")}
            value={compact(t.total_token_activity)}
            hint={tr("{models} model calls · {tools} tool calls", {
              models: t.llm_calls,
              tools: t.tool_calls,
            })}
            icon="↗"
          />
          <Stat
            label={tr("API-equivalent cost")}
            value={money(t.estimated_api_cost)}
            hint={tr("API workload value · subscription bill unknown")}
            icon="$"
          />
          <Stat
            label={tr("Duration")}
            value={duration(t.duration_seconds)}
            hint={t.source_surface}
            icon="◴"
          />
        </div>
        <section className="card note">
          <h2>{tr("Execution and billing")}</h2>
          <p>
            {t.client_id} · {tr(t.surface || "unknown surface")} ·{" "}
            {tr(t.runtime || "unknown runtime")} ·{" "}
            {tr(t.integration_type || "unknown integration")}
          </p>
          <p>
            {tr("Providers:")} {t.providers.join(", ") || t.provider}
            {tr(". API-equivalent estimate:")} {money(t.estimated_api_cost)}
            {tr(". Provider-reported cost:")} {money(t.observed_provider_cost)}
            {tr(". Subscription bill: unknown.")}
          </p>
          {t.unpriced_requests > 0 && (
            <p>
              {t.unpriced_requests}{" "}
              {tr("calls have incomplete pricing. Known components:")}{" "}
              {money(t.priced_partial_cost)}.
            </p>
          )}
          <dl>
            {Object.entries(t.usage).map(([name, usage]) => (
              <React.Fragment key={name}>
                <dt>{tr(name.replaceAll("_", " "))}</dt>
                <dd>
                  {usage.total == null ? tr("Unknown") : num(usage.total)}
                  {usage.unknown_calls > 0 &&
                    tr(" · missing in {count} calls", {
                      count: usage.unknown_calls,
                    })}
                </dd>
              </React.Fragment>
            ))}
          </dl>
        </section>
        <h2>{tr("Provider quota evidence")}</h2>
        {t.quota_by_provider.map((q) => (
          <p key={q.provider + q.account}>
            {q.provider} / {q.account}:{" "}
            {q.delta.length
              ? q.delta.map((d) => `${d.name}: ${deltaLabel(d)}`).join(" · ")
              : tr("No matching quota snapshots")}
          </p>
        ))}
        <h2>{tr("Model-call pricing provenance")}</h2>
        {t.events
          ?.filter((e) => e.kind === "llm")
          .map((e) => (
            <details className="card pricing-call" key={e.id}>
              <summary>
                {e.provider} / {e.model} ·{" "}
                {tr(e.pricing?.confidence || "legacy / unknown")} ·{" "}
                {money(e.pricing?.total ?? e.pricing?.usd)}
              </summary>
              <p>
                {tr("Rule:")}{" "}
                {e.pricing?.pricing_rule_id ||
                  tr("Historical estimate / unavailable")}
              </p>
              <p className="hash">
                {tr("Catalog:")}{" "}
                {e.pricing?.catalog_version ||
                  e.pricing?.version ||
                  tr("Unavailable")}
              </p>
              {(e.pricing?.components || []).map((c: any) => (
                <p key={c.metric}>
                  {c.metric}: {c.quantity} × {c.rate} / {c.unit} = ${c.subtotal}
                </p>
              ))}
              {[
                ...(e.pricing?.assumptions || []),
                ...(e.pricing?.warnings || []),
                ...(e.pricing?.notes || []),
              ].map((message: string, index: number) => (
                <p key={index}>{tr(message)}</p>
              ))}
              {e.pricing?.source?.url && (
                <a href={e.pricing.source.url} target="_blank" rel="noreferrer">
                  {tr("Official pricing source ↗")}
                </a>
              )}
            </details>
          ))}
        <h2>{tr("Token breakdown")}</h2>
        <div className="detail-tokens">
          {Object.entries(t.tokens).map(([k, v]) => (
            <div key={k}>
              <span>{tr(k.replaceAll("_", " "))}</span>
              <b>{num(v)}</b>
            </div>
          ))}
        </div>
        <div className="detail-grid">
          <Breakdown
            title={tr("Agent / subagent usage")}
            data={Object.fromEntries(
              Object.entries(t.agents).map(([k, v]) => [
                k,
                Object.values(v).reduce((a, b) => a + b, 0),
              ]),
            )}
          />
          <Breakdown
            title={tr("Model usage")}
            data={Object.fromEntries(
              Object.entries(t.models).map(([k, v]) => [
                k,
                Object.values(v).reduce((a, b) => a + b, 0),
              ]),
            )}
          />
        </div>
        <h2>{tr("Primary provider quota before → after")}</h2>
        {t.quota_delta.length ? (
          t.quota_delta.map((d) => (
            <div className="delta-row" key={d.name}>
              <b>{d.name}</b>
              <span>
                {num(d.before)}% → {num(d.after)}%
              </span>
              <strong>{deltaLabel(d)}</strong>
              <Badge>
                {d.source_before} / {d.source_after}
              </Badge>
            </div>
          ))
        ) : (
          <p className="muted">
            {tr("No matching snapshots bracketing this task.")}
          </p>
        )}
        <p className="footnote">
          {tr(
            "Account window change. Concurrent work can contribute; resets cannot produce a reliable single delta.",
          )}
        </p>
        <h2>{tr("Context")}</h2>
        <dl>
          <dt>{tr("Session")}</dt>
          <dd>{t.session_id}</dd>
          <dt>{tr("Repository")}</dt>
          <dd>{t.repository || tr("Not supplied")}</dd>
          <dt>{tr("Branch")}</dt>
          <dd>{t.git_branch || tr("Not supplied / detached HEAD")}</dd>
          <dt>{tr("Start commit")}</dt>
          <dd>{t.git_commit_start || tr("Not supplied")}</dd>
          <dt>{tr("End commit")}</dt>
          <dd>{t.git_commit_end || tr("Not supplied")}</dd>
          <dt>{tr("Started")}</dt>
          <dd>{formatDateTime(t.started_at)}</dd>
          <dt>{tr("Provider-emitted cost")}</dt>
          <dd>
            {money(t.observed_provider_cost)}{" "}
            {tr("· provider estimate, not a subscription bill")}
          </dd>
          <dt>{tr("Pricing coverage")}</dt>
          <dd>
            {t.unpriced_requests} {tr("unpriced requests")}
          </dd>
        </dl>
        <h2>{tr("Deep trace investigation")}</h2>
        {t.phoenix_trace_ids.length ? (
          t.phoenix_trace_ids.map((id) => (
            <div className="trace-link" key={id}>
              <code>{id}</code>
              <a
                className="button"
                href={phoenix}
                target="_blank"
                rel="noreferrer"
              >
                {tr("Find in Phoenix ↗")}
              </a>
            </div>
          ))
        ) : (
          <p className="muted">
            {tr(
              "No trace context received. Enable beta traces or send generic OTLP.",
            )}
          </p>
        )}
        <p className="footnote">
          {tr(
            "Use the trace ID to filter Phoenix. V1 avoids relying on an unstable project-specific deep-link route.",
          )}
        </p>
        <details>
          <summary>
            {tr("Request ledger ·")} {t.events?.length || 0} {tr("records")}
          </summary>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>{tr("Kind")}</th>
                  <th>{tr("Agent")}</th>
                  <th>{tr("Model")}</th>
                  <th>{tr("Tokens")}</th>
                </tr>
              </thead>
              <tbody>
                {t.events
                  ?.filter((e) => e.kind === "llm" || e.kind === "tool")
                  .map((e) => (
                    <tr key={e.id}>
                      <td>{tr(e.kind)}</td>
                      <td>{e.agent}</td>
                      <td>{e.model}</td>
                      <td>
                        {num(
                          Object.values(e.tokens).reduce((a, b) => a + b, 0),
                        )}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </details>
      </section>
    </div>
  );
}
createRoot(document.getElementById("root")!).render(<App />);

function PricingSettings({
  status,
  onSynced,
}: {
  status: any;
  onSynced: () => void;
}) {
  const [notice, setNotice] = useState(""),
    [busy, setBusy] = useState(false);
  async function syncPricing() {
    setBusy(true);
    try {
      await api("/pricing/sync", { method: "POST" });
      setNotice(
        tr("Bundled pricing synchronized. Stored estimates are preserved."),
      );
      onSynced();
    } catch (e) {
      setNotice(String(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="card note pricing-settings">
      <h2>{tr("Versioned pricing registry")}</h2>
      <Badge tone={status?.in_sync ? "green" : "neutral"}>
        {status?.in_sync ? tr("Synchronized") : tr("Sync needed")}
      </Badge>
      <p>
        {status?.providers} {tr("providers ·")} {status?.models}{" "}
        {tr("models ·")} {status?.rules} {tr("pricing rules")}
      </p>
      <dl>
        <dt>{tr("Bundled catalog")}</dt>
        <dd className="hash">{status?.bundled_hash}</dd>
        <dt>{tr("Active database catalog")}</dt>
        <dd className="hash">{status?.database_hash || tr("Not imported")}</dd>
        <dt>{tr("Last sync")}</dt>
        <dd>
          {status?.last_sync ? formatDateTime(status.last_sync) : tr("Never")}
        </dd>
      </dl>
      <p>
        {tr(
          "New calls use the active catalog. Each estimate keeps its original rule, catalog and component costs. Sync imports the registry shipped with this release.",
        )}
      </p>
      <button
        className="button dark"
        disabled={busy}
        onClick={() => void syncPricing()}
      >
        {busy ? tr("Synchronizing…") : tr("Sync bundled pricing")}
      </button>
      {notice && <p role="status">{notice}</p>}
    </section>
  );
}
function CostOverview({ overview: o }: { overview: Overview }) {
  return (
    <>
      <div className="stat-grid cost-stats">
        {[
          ["API equivalent today", o.cost_today],
          ["API equivalent this week", o.cost_week],
          ["API equivalent this month", o.cost_month],
        ].map(([name, cost]) => (
          <Stat
            key={String(name)}
            label={tr(String(name))}
            value={money((cost as any).estimated_api_equivalent_cost)}
            hint={
              (cost as any).unpriced_requests
                ? (cost as any).priced_partial_cost == null
                  ? tr("No priced estimate · {count} incomplete", {
                      count: (cost as any).unpriced_requests,
                    })
                  : tr("{cost} priced · {count} incomplete", {
                      cost: money((cost as any).priced_partial_cost),
                      count: (cost as any).unpriced_requests,
                    })
                : tr("Estimated workload value · USD")
            }
            icon="$"
          />
        ))}
        <Stat
          label={tr("Calls with incomplete pricing")}
          value={num(o.unpriced_requests)}
          hint={tr("Missing telemetry or a matching price")}
          icon="?"
        />
      </div>
      <p className="cost-explanation">
        {tr(
          "API-equivalent costs describe workload value. Subscription charges and incremental bills remain unknown.",
        )}
      </p>
      <div className="cost-grid">
        {["client_id", "provider", "model", "project", "agent"].map((field) => (
          <section className="card breakdown" key={field}>
            <CardTitle
              title={tr("Cost by {dimension}", {
                dimension: tr(field === "client_id" ? "client" : field),
              })}
              detail={tr("API-equivalent USD")}
            />
            {Object.entries(o.costs?.[field] || {}).map(([name, cost]) => (
              <div className="cost-row" key={name}>
                <span>
                  {name}
                  <small>
                    {tr("{count} calls · {tokens} known tokens", {
                      count: cost.calls,
                      tokens: compact(cost.token_activity),
                    })}
                  </small>
                </span>
                <b>
                  {money(cost.estimated_api_equivalent_cost)}
                  {cost.unpriced_requests > 0 && (
                    <small>
                      {cost.priced_partial_cost == null
                        ? tr("No priced estimate · {count} incomplete", {
                            count: cost.unpriced_requests,
                          })
                        : tr("{cost} priced · {count} incomplete", {
                            cost: money(cost.priced_partial_cost),
                            count: cost.unpriced_requests,
                          })}
                    </small>
                  )}
                </b>
              </div>
            ))}
          </section>
        ))}
        <section className="card breakdown">
          <CardTitle
            title={tr("Pricing coverage")}
            detail={tr("Confidence and cost components")}
          />
          {Object.entries(o.pricing_confidence || {}).map(([name, n]) => (
            <div className="cost-row" key={name}>
              <span>{tr(name)}</span>
              <b>{tr("{count} calls", { count: Number(n) })}</b>
            </div>
          ))}
          {Object.entries(o.cost_components || {}).map(([name, cost]) => (
            <div className="cost-row" key={name}>
              <span>{tr(name.replaceAll("_", " "))}</span>
              <b>{money(cost)}</b>
            </div>
          ))}
          {Object.entries(o.unknown_models || {}).map(([name, n]) => (
            <p key={name}>
              {name}:{" "}
              {tr("{count} calls with incomplete pricing", {
                count: Number(n),
              })}
            </p>
          ))}
        </section>
      </div>
    </>
  );
}

function IntegrationPrompt({
  client,
}: {
  client: { id: string; name: string };
}) {
  const [copied, setCopied] = useState(false);
  const [failed, setFailed] = useState(false);
  const guide =
    client.id === "generic_otlp"
      ? "integrations/generic-otel/README.md"
      : `docs/integrations/${client.id.replaceAll("_", "-")}.md`;
  const prompt = tr(
    "Configure {client} to send metadata to my local TraceQuota installation. Read {guide}. Verify http://127.0.0.1:8080/health and the local Docker services first. Back up existing user settings and merge the integration without changing authentication, permissions or unrelated settings. Use loopback endpoints only; OTLP HTTP is http://127.0.0.1:4318. Keep prompt, response, tool-content and credential capture disabled. Follow the documented capability limits; do not invent token, cost or quota data. Do not make model requests for testing. Validate configuration without consuming provider quota, then explain which new session or ordinary user activity is needed to see real telemetry.",
    {
      client: client.name,
      guide: `https://github.com/ruanpato/tracequota/blob/main/${guide}`,
    },
  );
  return (
    <details className="integration-prompt">
      <summary>{tr("Set up with your coding agent")}</summary>
      <p>
        {tr(
          "Copy this prompt into the agent you want to configure. Review its local settings changes.",
        )}
      </p>
      <textarea
        aria-label={tr("Integration prompt")}
        readOnly
        value={prompt}
        rows={10}
      />
      <button
        type="button"
        className="button"
        onClick={async () => {
          try {
            await navigator.clipboard.writeText(prompt);
            setCopied(true);
            setFailed(false);
          } catch {
            setFailed(true);
          }
        }}
      >
        {tr("Copy prompt")}
      </button>
      <p role="status">
        {failed
          ? tr("Select and copy the prompt manually.")
          : copied
            ? tr("Prompt copied.")
            : ""}
      </p>
    </details>
  );
}
