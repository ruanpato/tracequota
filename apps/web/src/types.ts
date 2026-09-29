// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Ruan Pato

export type Tokens = {
  input: number;
  output: number;
  cache_read: number;
  cache_write: number;
};
export type Window = {
  name: string;
  type: string;
  used_percent: number;
  remaining_percent: number;
  reset_at: string | null;
};
export type Snapshot = {
  id: string;
  provider: string;
  account: string;
  captured_at: string;
  source: string;
  demo: boolean;
  windows: Window[];
};
export type Delta = {
  name: string;
  before: number;
  after: number;
  delta_pp: number | null;
  reset_crossed: boolean;
  source_before: string;
  source_after: string;
};
export type Task = {
  id: string;
  title: string;
  project: string;
  client_id: string;
  client_version?: string;
  surface: string;
  runtime: string;
  integration_type: string;
  providers: string[];
  usage: Record<
    string,
    { total: number | null; known_calls: number; unknown_calls: number }
  >;
  quota_by_provider: Array<{
    provider: string;
    account: string;
    before: Snapshot | null;
    after: Snapshot | null;
    delta: Delta[];
  }>;
  cost_components: Record<string, string>;
  pricing_confidence: Record<string, number>;
  provider: string;
  session_id: string;
  kind: string;
  status: string;
  demo: boolean;
  started_at: string;
  completed_at: string | null;
  duration_seconds: number | null;
  tokens: Tokens;
  total_token_activity: number;
  estimated_api_cost: string | number | null;
  observed_provider_cost: string | number | null;
  priced_partial_cost: string | number | null;
  unpriced_requests: number;
  models: Record<string, Tokens>;
  agents: Record<string, Tokens>;
  main_agent_activity: number;
  subagent_activity: number;
  llm_calls: number;
  tool_calls: number;
  quota_before: Snapshot | null;
  quota_after: Snapshot | null;
  quota_delta: Delta[];
  repository: string | null;
  git_branch: string | null;
  git_commit_start: string | null;
  git_commit_end?: string | null;
  phoenix_trace_ids: string[];
  source_surface: string;
  events?: Array<{
    id: string;
    kind: string;
    agent: string;
    model: string;
    timestamp: string;
    tokens: Tokens;
    pricing: any;
    usage?: any;
    provider?: string;
    client_id?: string;
  }>;
};
export type Overview = {
  costs: Record<string, Record<string, any>>;
  cost_today: any;
  cost_week: any;
  cost_month: any;
  unpriced_requests: number;
  unknown_models: Record<string, number>;
  pricing_confidence: Record<string, number>;
  cost_components: Record<string, string>;
  tokens_today: number;
  tokens_week: number;
  tasks_today: number;
  sessions: number;
  projects: number;
  tasks: Task[];
  quota: Snapshot[];
  models: Record<string, number>;
  agents: Record<string, number>;
  project_usage: Record<string, number>;
};
export const formatNumber = (n: number) =>
  new Intl.NumberFormat("en-US").format(n);
export const formatDateTime = (value: string) =>
  new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    second: "2-digit",
    timeZone: "UTC",
    timeZoneName: "short",
  }).format(new Date(value));
export const compact = (n: number) =>
  new Intl.NumberFormat("en-US", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(n);
export const money = (n: number | string | null | undefined) =>
  n == null
    ? "Unknown"
    : new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
        maximumFractionDigits: 3,
      }).format(Number(n));
export const duration = (n: number | null) =>
  n === null
    ? "In progress"
    : n < 60
      ? `${Math.round(n)}s`
      : `${Math.floor(n / 60)}m ${Math.round(n % 60)}s`;
export function deltaLabel(d: Delta | undefined) {
  return !d
    ? "No snapshots"
    : d.reset_crossed
      ? "Reset crossed"
      : d.delta_pp === null
        ? "Unknown"
        : `${d.delta_pp >= 0 ? "+" : ""}${d.delta_pp} pp`;
}
export function matchesSearch(task: Task, search: string) {
  return [
    task.title,
    task.project,
    task.session_id,
    task.client_id,
    task.provider,
    ...Object.keys(task.models),
    ...Object.keys(task.agents),
  ]
    .join(" ")
    .toLowerCase()
    .includes(search.toLowerCase());
}
