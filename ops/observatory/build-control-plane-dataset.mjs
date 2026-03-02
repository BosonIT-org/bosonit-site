#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";

const SCRIPT_DIR = path.dirname(new URL(import.meta.url).pathname);
const REPO_ROOT = path.resolve(SCRIPT_DIR, "..", "..");

const SOURCE_CANDIDATES = [
  process.env.HABITAT_OBSERVATORY_ROOT,
  "/Users/kennethjones/bosonit-habitat-observatory",
  path.join(REPO_ROOT, "observatory"),
].filter(Boolean);

const OUTPUT_FILE = path.join(REPO_ROOT, "public", "observatory", "control-plane.latest.json");

function nowIso() {
  return new Date().toISOString();
}

function exists(filePath) {
  return fs.existsSync(filePath);
}

function readJson(filePath, warnings, fallback = null) {
  if (!exists(filePath)) {
    warnings.push(`missing_file:${filePath}`);
    return fallback;
  }
  try {
    return JSON.parse(fs.readFileSync(filePath, "utf8"));
  } catch (error) {
    warnings.push(`json_parse_failed:${filePath}:${String(error.message || error)}`);
    return fallback;
  }
}

function readJsonl(filePath, warnings) {
  if (!exists(filePath)) {
    warnings.push(`missing_file:${filePath}`);
    return [];
  }
  const lines = fs.readFileSync(filePath, "utf8").split("\n").map((line) => line.trim()).filter(Boolean);
  const parsed = [];
  for (const [index, line] of lines.entries()) {
    try {
      parsed.push(JSON.parse(line));
    } catch (error) {
      warnings.push(`jsonl_parse_failed:${filePath}:line_${index + 1}:${String(error.message || error)}`);
    }
  }
  return parsed;
}

function safeNum(value) {
  return Number.isFinite(Number(value)) ? Number(value) : 0;
}

function normalizeHeartbeatHosts(hosts) {
  const rows = Array.isArray(hosts) ? hosts : [];
  return rows.map((host) => ({
    host_id: host.host_id || "unknown",
    checked_at_utc: host.checked_at_utc || null,
    reachable: Boolean(host.reachable),
    gateway_running: Boolean(host.gateway_running),
    gateway_status: host.gateway_status || "",
    telegram_token_present: Boolean(host.telegram_token_present),
    telegram_bot_username: host.telegram_bot_username || "",
    issue_count: safeNum(host.gateway_error_count ?? host.issue_count ?? 0),
  }));
}

function sortByTimestampDesc(items, key = "timestamp_utc") {
  return [...items].sort((a, b) => {
    const aMs = Date.parse(a?.[key] || "") || 0;
    const bMs = Date.parse(b?.[key] || "") || 0;
    return bMs - aMs;
  });
}

function findEvidenceRoot() {
  for (const candidate of SOURCE_CANDIDATES) {
    const evidence = path.join(candidate, "evidence");
    if (exists(evidence)) {
      return {
        observatoryRoot: candidate,
        evidenceRoot: evidence,
      };
    }
  }
  const fallbackRoot = path.join(REPO_ROOT, "observatory");
  return {
    observatoryRoot: fallbackRoot,
    evidenceRoot: path.join(fallbackRoot, "evidence"),
  };
}

function walkFiles(root, fileName) {
  if (!exists(root)) {
    return [];
  }
  const stack = [root];
  const matches = [];
  while (stack.length > 0) {
    const current = stack.pop();
    const entries = fs.readdirSync(current, { withFileTypes: true });
    for (const entry of entries) {
      const absolute = path.join(current, entry.name);
      if (entry.isDirectory()) {
        stack.push(absolute);
      } else if (entry.isFile() && entry.name === fileName) {
        matches.push(absolute);
      }
    }
  }
  return matches;
}

function summarizeHeartbeat(status) {
  const hostRows = normalizeHeartbeatHosts(status?.hosts);
  return {
    stage: status?.stage || "unknown",
    ok: Boolean(status?.ok),
    checked_at_utc: status?.checked_at_utc || null,
    monitored_hosts: Array.isArray(status?.monitored_hosts) ? status.monitored_hosts : [],
    expected_ingress_host: status?.expected_ingress_host || null,
    token_policy: status?.token_policy || null,
    health: status?.health || null,
    issues: Array.isArray(status?.issues) ? status.issues : [],
    advisory_mode: Boolean(status?.advisory_mode),
    hosts: hostRows,
  };
}

function summarizeDispatch(events) {
  if (events.length === 0) {
    return {
      total_events: 0,
      status_breakdown: {},
      host_breakdown: {},
      recent_cases: [],
      success_rate: 0,
    };
  }

  const sorted = sortByTimestampDesc(events);
  const statusBreakdown = {};
  const hostBreakdown = {};
  const caseMap = new Map();
  let successCount = 0;

  for (const event of events) {
    const status = event.status || "unknown";
    const host = event.host || "unknown";
    statusBreakdown[status] = (statusBreakdown[status] || 0) + 1;
    hostBreakdown[host] = (hostBreakdown[host] || 0) + 1;
    if (status === "success") {
      successCount += 1;
    }

    const caseId = event.case_id || "unknown";
    const current = caseMap.get(caseId) || {
      case_id: caseId,
      request_owner: event.request_owner || "",
      selected_model: event.selected_model || "",
      selected_provider: event.selected_provider || "",
      first_seen_utc: event.timestamp_utc || null,
      latest_seen_utc: event.timestamp_utc || null,
      statuses: new Set(),
      hosts: new Set(),
      events: 0,
    };
    current.events += 1;
    current.statuses.add(status);
    current.hosts.add(host);

    const ts = Date.parse(event.timestamp_utc || "") || 0;
    const firstTs = Date.parse(current.first_seen_utc || "") || 0;
    const latestTs = Date.parse(current.latest_seen_utc || "") || 0;
    if (firstTs === 0 || (ts !== 0 && ts < firstTs)) {
      current.first_seen_utc = event.timestamp_utc || current.first_seen_utc;
    }
    if (latestTs === 0 || ts > latestTs) {
      current.latest_seen_utc = event.timestamp_utc || current.latest_seen_utc;
      current.selected_model = event.selected_model || current.selected_model;
      current.selected_provider = event.selected_provider || current.selected_provider;
      current.request_owner = event.request_owner || current.request_owner;
    }
    caseMap.set(caseId, current);
  }

  const recentCases = sortByTimestampDesc(
    Array.from(caseMap.values()).map((item) => ({
      ...item,
      statuses: Array.from(item.statuses).sort(),
      hosts: Array.from(item.hosts).sort(),
    })),
    "latest_seen_utc",
  ).slice(0, 20);

  return {
    total_events: events.length,
    status_breakdown: statusBreakdown,
    host_breakdown: hostBreakdown,
    recent_cases: recentCases,
    success_rate: Number((successCount / events.length).toFixed(4)),
    latest_event_utc: sorted[0]?.timestamp_utc || null,
  };
}

function summarizeGovernor(events) {
  if (events.length === 0) {
    return {
      total_events: 0,
      fallback_used_count: 0,
      denial_count: 0,
      latest: null,
      top_profiles: [],
      avg_token_spend_estimate: 0,
    };
  }

  const sorted = sortByTimestampDesc(events);
  const latest = sorted[0];
  const profileCounts = {};
  const providerCounts = {};
  let fallbackCount = 0;
  let denialCount = 0;
  let tokenTotal = 0;

  for (const event of events) {
    const profile = event.selected_profile_id || "unknown";
    const provider = event.selected_provider || "unknown";
    profileCounts[profile] = (profileCounts[profile] || 0) + 1;
    providerCounts[provider] = (providerCounts[provider] || 0) + 1;
    if (event.fallback_used) {
      fallbackCount += 1;
    }
    if (event.regulatory_verdict && event.regulatory_verdict !== "APPROVE") {
      denialCount += 1;
    }
    tokenTotal += safeNum(event.token_spend_estimate);
  }

  const topProfiles = Object.entries(profileCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([profile, count]) => ({ profile, count }));

  const topProviders = Object.entries(providerCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([provider, count]) => ({ provider, count }));

  return {
    total_events: events.length,
    fallback_used_count: fallbackCount,
    denial_count: denialCount,
    avg_token_spend_estimate: Number((tokenTotal / events.length).toFixed(2)),
    top_profiles: topProfiles,
    top_providers: topProviders,
    latest: latest
      ? {
          timestamp_utc: latest.timestamp_utc || null,
          selected_profile_id: latest.selected_profile_id || "",
          selected_provider: latest.selected_provider || "",
          selected_model: latest.selected_model || "",
          auth_profile: latest.auth_profile || "",
          data_classification: latest.data_classification || "",
          impact_level: latest.impact_level || "",
          regulatory_verdict: latest.regulatory_verdict || "",
          fallback_used: Boolean(latest.fallback_used),
          token_spend_estimate: safeNum(latest.token_spend_estimate),
          token_guard: latest.token_guard || null,
        }
      : null,
  };
}

function summarizeSystemChanges(events) {
  const sorted = sortByTimestampDesc(events);
  const severityCounts = {};
  const categoryCounts = {};
  for (const event of events) {
    const severity = event.severity || "unknown";
    const category = event.category || "unknown";
    severityCounts[severity] = (severityCounts[severity] || 0) + 1;
    categoryCounts[category] = (categoryCounts[category] || 0) + 1;
  }

  return {
    total_events: events.length,
    severity_breakdown: severityCounts,
    category_breakdown: categoryCounts,
    recent: sorted.slice(0, 20).map((event) => ({
      event_id: event.event_id || "",
      timestamp_utc: event.timestamp_utc || null,
      category: event.category || "",
      severity: event.severity || "",
      summary: event.summary || "",
      actor: event.actor || "",
      status: event.status || "",
    })),
  };
}

function summarizeCiReport(ciReport, ciSnapshot) {
  const changes = ciReport?.changes || {};
  const added = Array.isArray(changes.added) ? changes.added : [];
  const modified = Array.isArray(changes.modified) ? changes.modified : [];
  const removed = Array.isArray(changes.removed) ? changes.removed : [];

  function classBreakdown(items, mode) {
    const buckets = {};
    for (const item of items) {
      const source = mode === "modified" ? (item.after || item.before || {}) : item;
      const ciClass = source?.ci_class || "unknown";
      buckets[ciClass] = (buckets[ciClass] || 0) + 1;
    }
    return buckets;
  }

  const snapshotItems = ciSnapshot?.items && typeof ciSnapshot.items === "object" ? ciSnapshot.items : {};

  return {
    generated_at: ciReport?.generated_at || ciSnapshot?.generated_at || null,
    advisory_mode: Boolean(ciReport?.advisory_mode),
    counts: {
      added: added.length,
      modified: modified.length,
      removed: removed.length,
      snapshot_items: Object.keys(snapshotItems).length,
    },
    class_breakdown: {
      added: classBreakdown(added, "added"),
      modified: classBreakdown(modified, "modified"),
      removed: classBreakdown(removed, "removed"),
    },
    recent_examples: {
      added: added.slice(0, 8),
      modified: modified.slice(0, 8),
      removed: removed.slice(0, 8),
    },
  };
}

function summarizeWorkflowRuns(evidenceRoot, warnings) {
  const workflowRoot = path.join(evidenceRoot, "BosonIT-org");
  const metadataFiles = walkFiles(workflowRoot, "metadata.json");
  const runs = [];
  for (const file of metadataFiles) {
    const payload = readJson(file, warnings, null);
    if (!payload || typeof payload !== "object") {
      continue;
    }
    runs.push({
      source_repository: payload.source_repository || "",
      workflow_name: payload.workflow_name || "unknown",
      workflow_run_id: safeNum(payload.workflow_run_id),
      workflow_run_attempt: safeNum(payload.workflow_run_attempt),
      conclusion: payload.conclusion || "unknown",
      workflow_url: payload.workflow_url || "",
      published_at_utc: payload.published_at_utc || null,
      evidence_path: path.relative(evidenceRoot, file),
    });
  }

  const sorted = sortByTimestampDesc(runs, "published_at_utc");
  const byConclusion = {};
  const byWorkflow = {};
  let activeCount = 0;
  let failureCount = 0;
  const activeConclusions = new Set(["queued", "in_progress", "waiting", "requested"]);
  const nowMs = Date.now();
  const recentFailureWindow = 24 * 60 * 60 * 1000;
  let failuresLast24h = 0;

  for (const run of runs) {
    const conclusion = run.conclusion || "unknown";
    byConclusion[conclusion] = (byConclusion[conclusion] || 0) + 1;
    const workflowKey = `${run.source_repository || "unknown"}:${run.workflow_name || "unknown"}`;
    byWorkflow[workflowKey] = (byWorkflow[workflowKey] || 0) + 1;

    if (activeConclusions.has(conclusion)) {
      activeCount += 1;
    }
    if (conclusion !== "success") {
      failureCount += 1;
      const ts = Date.parse(run.published_at_utc || "") || 0;
      if (ts > 0 && nowMs - ts <= recentFailureWindow) {
        failuresLast24h += 1;
      }
    }
  }

  const topWorkflows = Object.entries(byWorkflow)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)
    .map(([key, count]) => ({ workflow: key, count }));

  return {
    total_runs: runs.length,
    active_runs: activeCount,
    non_success_runs: failureCount,
    non_success_runs_last_24h: failuresLast24h,
    by_conclusion: byConclusion,
    top_workflows: topWorkflows,
    recent_runs: sorted.slice(0, 30),
  };
}

function computeGovernanceVerdict(governorLatest) {
  const dataClass = governorLatest?.data_classification || "internal";
  const impact = governorLatest?.impact_level || "advisory";

  const base = {
    data_class: dataClass,
    impact_level: impact,
    required_controls: ["logging_and_traceability", "deterministic_output_checks"],
    approval_required: false,
    block_reason: null,
    verdict: "allow",
  };

  if (dataClass === "restricted") {
    return {
      ...base,
      verdict: "deny",
      approval_required: true,
      required_controls: [...base.required_controls, "no_external_processing", "human_approval_record"],
      block_reason: "restricted_data_external_processing_blocked",
    };
  }

  if (impact === "write" || impact === "deploy" || impact === "security") {
    return {
      ...base,
      verdict: "require_approval",
      approval_required: true,
      required_controls: [...base.required_controls, "human_approval_record", "rollback_plan_required"],
      block_reason: "high_impact_action_requires_approval",
    };
  }

  if (dataClass === "confidential") {
    return {
      ...base,
      verdict: "allow_with_controls",
      required_controls: [...base.required_controls, "redact_or_tokenize_sensitive_data"],
    };
  }

  return base;
}

function main() {
  const warnings = [];
  const source = findEvidenceRoot();
  const heartbeatStatus = readJson(path.join(source.evidenceRoot, "heartbeat", "agent_heartbeat_status.json"), warnings, {});
  const heartbeatState = readJson(path.join(source.evidenceRoot, "heartbeat", "agent_heartbeat_state.json"), warnings, {});
  const ciSnapshot = readJson(path.join(source.evidenceRoot, "heartbeat", "ci_snapshot.json"), warnings, {});
  const ciReport = readJson(path.join(source.evidenceRoot, "heartbeat", "ci_report.json"), warnings, {});

  const dispatchEvents = readJsonl(path.join(source.evidenceRoot, "windmill", "agent_dispatch_events.jsonl"), warnings);
  const governorEvents = readJsonl(path.join(source.evidenceRoot, "windmill", "agent_cost_governor_events.jsonl"), warnings);
  const heartbeatEvents = readJsonl(path.join(source.evidenceRoot, "windmill", "agent_heartbeat_events.jsonl"), warnings);
  const systemChangeEvents = readJsonl(path.join(source.evidenceRoot, "windmill", "system_change_events.jsonl"), warnings);

  const heartbeatSummary = summarizeHeartbeat(heartbeatStatus);
  const dispatchSummary = summarizeDispatch(dispatchEvents);
  const governorSummary = summarizeGovernor(governorEvents);
  const ciSummary = summarizeCiReport(ciReport, ciSnapshot);
  const workflowSummary = summarizeWorkflowRuns(source.evidenceRoot, warnings);
  const systemSummary = summarizeSystemChanges(systemChangeEvents);
  const latestHeartbeatEvent = sortByTimestampDesc(heartbeatEvents, "checked_at_utc")[0] || null;

  if (latestHeartbeatEvent) {
    const latestMs = Date.parse(latestHeartbeatEvent.checked_at_utc || "") || 0;
    const summaryMs = Date.parse(heartbeatSummary.checked_at_utc || "") || 0;
    if (latestMs >= summaryMs) {
      heartbeatSummary.stage = latestHeartbeatEvent.stage || heartbeatSummary.stage;
      heartbeatSummary.ok = Boolean(latestHeartbeatEvent.ok);
      heartbeatSummary.checked_at_utc = latestHeartbeatEvent.checked_at_utc || heartbeatSummary.checked_at_utc;
      heartbeatSummary.monitored_hosts = Array.isArray(latestHeartbeatEvent.monitored_hosts)
        ? latestHeartbeatEvent.monitored_hosts
        : heartbeatSummary.monitored_hosts;
      heartbeatSummary.expected_ingress_host = latestHeartbeatEvent.expected_ingress_host || heartbeatSummary.expected_ingress_host;
      heartbeatSummary.token_policy = latestHeartbeatEvent.token_policy || heartbeatSummary.token_policy;
      heartbeatSummary.health = latestHeartbeatEvent.health || heartbeatSummary.health;
      heartbeatSummary.issues = Array.isArray(latestHeartbeatEvent.issues) ? latestHeartbeatEvent.issues : heartbeatSummary.issues;
      heartbeatSummary.advisory_mode = Boolean(latestHeartbeatEvent.advisory_mode);
      heartbeatSummary.hosts = normalizeHeartbeatHosts(latestHeartbeatEvent.hosts);
    }
  }

  const dashboard = {
    schema_version: "2026-03-02.control-plane.v1",
    generated_at_utc: nowIso(),
    source: {
      observatory_root: source.observatoryRoot,
      evidence_root: source.evidenceRoot,
      candidates_checked: SOURCE_CANDIDATES,
      warnings,
    },
    habitat: {
      heartbeat_status: heartbeatSummary,
      heartbeat_state: heartbeatState || {},
      heartbeat_event_count: heartbeatEvents.length,
      latest_heartbeat_event_utc: latestHeartbeatEvent?.checked_at_utc || null,
    },
    inflight: {
      workflows: workflowSummary,
      dispatch: dispatchSummary,
    },
    routing: governorSummary,
    governance_verdict: computeGovernanceVerdict(governorSummary.latest),
    ci: ciSummary,
    system_changes: systemSummary,
  };

  fs.mkdirSync(path.dirname(OUTPUT_FILE), { recursive: true });
  fs.writeFileSync(OUTPUT_FILE, `${JSON.stringify(dashboard, null, 2)}\n`, "utf8");

  console.log(
    JSON.stringify(
      {
        ok: true,
        output_file: OUTPUT_FILE,
        generated_at_utc: dashboard.generated_at_utc,
        evidence_root: source.evidenceRoot,
        warning_count: warnings.length,
      },
      null,
      2,
    ),
  );
}

main();
