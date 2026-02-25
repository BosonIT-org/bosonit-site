#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    raw = path.read_text(encoding="utf-8")
    if not raw.strip():
        return {}
    try:
        payload = json.loads(raw)
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _parse_log_timestamp(line: str) -> datetime | None:
    # expected format: 2026-02-23 01:58:26,522 INFO ...
    if len(line) < 23:
        return None
    prefix = line[:23]
    try:
        return datetime.strptime(prefix, "%Y-%m-%d %H:%M:%S,%f").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


@dataclass
class LogStats:
    exists: bool
    line_count: int
    runtime_seconds: float | None
    error_lines: int
    warning_lines: int
    fallback_detected: bool
    timeout_detected: bool
    protocol_error_detected: bool


def parse_log(log_path: Path) -> LogStats:
    if not log_path.exists():
        return LogStats(
            exists=False,
            line_count=0,
            runtime_seconds=None,
            error_lines=0,
            warning_lines=0,
            fallback_detected=False,
            timeout_detected=False,
            protocol_error_detected=False,
        )

    lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    first_ts: datetime | None = None
    last_ts: datetime | None = None
    error_lines = 0
    warning_lines = 0
    fallback_detected = False
    timeout_detected = False
    protocol_error_detected = False

    for line in lines:
        ts = _parse_log_timestamp(line)
        if ts is not None:
            if first_ts is None or ts < first_ts:
                first_ts = ts
            if last_ts is None or ts > last_ts:
                last_ts = ts
        upper = line.upper()
        lower = line.lower()
        if " ERROR " in upper:
            error_lines += 1
        if " WARNING " in upper or " WARN " in upper:
            warning_lines += 1
        if "fail-safe fallback" in lower:
            fallback_detected = True
        if "timed out" in lower:
            timeout_detected = True
        if "no agentmessage found in thread history" in lower:
            protocol_error_detected = True

    runtime_seconds: float | None = None
    if first_ts and last_ts:
        runtime_seconds = max(0.0, (last_ts - first_ts).total_seconds())

    return LogStats(
        exists=True,
        line_count=len(lines),
        runtime_seconds=runtime_seconds,
        error_lines=error_lines,
        warning_lines=warning_lines,
        fallback_detected=fallback_detected,
        timeout_detected=timeout_detected,
        protocol_error_detected=protocol_error_detected,
    )


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=True) + "\n")


def _read_history(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue
        if isinstance(row, dict):
            out.append(row)
    return out


def _ratio(rows: list[dict[str, Any]], key: str) -> float:
    if not rows:
        return 0.0
    hits = sum(1 for r in rows if bool(r.get(key)))
    return hits / float(len(rows))


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default


def _history_tail(rows: list[dict[str, Any]], n: int) -> list[dict[str, Any]]:
    if n <= 0:
        return []
    return rows[-n:]


def build_summary_md(payload: dict[str, Any]) -> str:
    run = payload["run"]
    rolling = payload["rolling"]
    slo = payload["slo"]
    assessment = payload["assessment"]
    log = payload["log"]

    lines: list[str] = []
    lines.append("## Habitat Warden Scorecard")
    lines.append("")
    lines.append(f"- Health: **{run['health']}**")
    lines.append(f"- Verdict: **{assessment.get('regulatory_verdict', 'UNKNOWN')}**")
    lines.append(f"- Requires approval: **{assessment.get('requires_approval', False)}**")
    lines.append(f"- Fallback detected: **{run['fallback_detected']}**")
    lines.append(f"- Timeout detected: **{run['timeout_detected']}**")
    lines.append(f"- Runtime seconds: **{log.get('runtime_seconds')}**")
    lines.append("")
    lines.append("### Rolling window")
    lines.append(f"- Runs analyzed: **{rolling['run_count']}**")
    lines.append(f"- Fallback rate: **{rolling['fallback_rate']:.2%}**")
    lines.append(f"- Timeout rate: **{rolling['timeout_rate']:.2%}**")
    lines.append(f"- Error-run rate: **{rolling['error_run_rate']:.2%}**")
    lines.append(f"- Avg runtime seconds: **{rolling['avg_runtime_seconds']:.2f}**")
    lines.append("")
    lines.append("### SLO checks")
    for check in slo["checks"]:
        status = "PASS" if check.get("ok", False) else "FAIL"
        lines.append(f"- {status}: {check['name']} ({check['actual']} vs target {check['target']})")
    lines.append("")
    return "\n".join(lines)


def emit_github_outputs(payload: dict[str, Any]) -> None:
    out_path = os.getenv("GITHUB_OUTPUT", "").strip()
    if not out_path:
        return
    p = Path(out_path)
    lines = [
        f"warden_health={payload['run']['health']}",
        f"warden_fallback_detected={str(payload['run']['fallback_detected']).lower()}",
        f"warden_timeout_detected={str(payload['run']['timeout_detected']).lower()}",
        f"warden_slo_pass={str(payload['slo']['pass']).lower()}",
        f"warden_rolling_fallback_rate={payload['rolling']['fallback_rate']:.6f}",
        f"warden_rolling_timeout_rate={payload['rolling']['timeout_rate']:.6f}",
        f"warden_rolling_error_rate={payload['rolling']['error_run_rate']:.6f}",
    ]
    with p.open("a", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Habitat Warden reliability/value scorecard.")
    parser.add_argument("--assessment-path", required=True)
    parser.add_argument("--log-path", required=True)
    parser.add_argument("--slo-path", required=True)
    parser.add_argument("--history-path", required=True)
    parser.add_argument("--history-tail-path", required=True)
    parser.add_argument("--output-path", required=True)
    parser.add_argument("--summary-path", required=True)
    parser.add_argument("--window-size", type=int, default=50)
    args = parser.parse_args()

    assessment_raw = _load_json(Path(args.assessment_path))
    log_stats = parse_log(Path(args.log_path))
    slo_cfg = _load_json(Path(args.slo_path))

    run_id = os.getenv("GITHUB_RUN_ID", "")
    run_attempt = os.getenv("GITHUB_RUN_ATTEMPT", "")
    pr_number = os.getenv("GITHUB_EVENT_PULL_REQUEST_NUMBER", "")
    verdict = str(assessment_raw.get("regulatory_verdict", "UNKNOWN"))
    requires_approval = bool(assessment_raw.get("requires_approval", False))

    run_entry: dict[str, Any] = {
        "timestamp": _now_iso(),
        "run_id": run_id,
        "run_attempt": run_attempt,
        "pr_number": pr_number,
        "verdict": verdict,
        "requires_approval": requires_approval,
        "fallback_detected": log_stats.fallback_detected,
        "timeout_detected": log_stats.timeout_detected,
        "protocol_error_detected": log_stats.protocol_error_detected,
        "error_run": log_stats.error_lines > 0,
        "runtime_seconds": log_stats.runtime_seconds,
        "assessment_present": bool(assessment_raw),
    }

    history_path = Path(args.history_path)
    _append_jsonl(history_path, run_entry)
    history_rows = _read_history(history_path)
    window_rows = _history_tail(history_rows, max(1, args.window_size))

    runtimes = [_safe_float(r.get("runtime_seconds"), -1.0) for r in window_rows]
    runtimes = [x for x in runtimes if x >= 0.0]
    avg_runtime = (sum(runtimes) / len(runtimes)) if runtimes else 0.0

    rolling = {
        "run_count": len(window_rows),
        "fallback_rate": _ratio(window_rows, "fallback_detected"),
        "timeout_rate": _ratio(window_rows, "timeout_detected"),
        "error_run_rate": _ratio(window_rows, "error_run"),
        "avg_runtime_seconds": avg_runtime,
    }

    max_runtime = _safe_float(slo_cfg.get("max_runtime_seconds"), 300.0)
    max_fallback_rate = _safe_float(slo_cfg.get("max_fallback_rate"), 0.2)
    max_timeout_rate = _safe_float(slo_cfg.get("max_timeout_rate"), 0.1)
    max_error_run_rate = _safe_float(slo_cfg.get("max_error_run_rate"), 0.2)

    runtime_actual = log_stats.runtime_seconds if log_stats.runtime_seconds is not None else -1.0
    checks = [
        {
            "name": "single_run_runtime_seconds",
            "target": f"<= {max_runtime}",
            "actual": f"{runtime_actual}",
            "ok": runtime_actual < 0 or runtime_actual <= max_runtime,
        },
        {
            "name": "rolling_fallback_rate",
            "target": f"<= {max_fallback_rate}",
            "actual": f"{rolling['fallback_rate']:.6f}",
            "ok": rolling["fallback_rate"] <= max_fallback_rate,
        },
        {
            "name": "rolling_timeout_rate",
            "target": f"<= {max_timeout_rate}",
            "actual": f"{rolling['timeout_rate']:.6f}",
            "ok": rolling["timeout_rate"] <= max_timeout_rate,
        },
        {
            "name": "rolling_error_run_rate",
            "target": f"<= {max_error_run_rate}",
            "actual": f"{rolling['error_run_rate']:.6f}",
            "ok": rolling["error_run_rate"] <= max_error_run_rate,
        },
    ]

    slo_pass = all(bool(c.get("ok", False)) for c in checks)
    if log_stats.fallback_detected or log_stats.timeout_detected:
        health = "RED"
    elif not slo_pass:
        health = "YELLOW"
    else:
        health = "GREEN"

    assessment = {
        "regulatory_verdict": verdict,
        "requires_approval": requires_approval,
        "critical_habitat_interference": bool(assessment_raw.get("critical_habitat_interference", False)),
        "mitigation_plan_verified": bool(assessment_raw.get("mitigation_plan_verified", False)),
    }
    log_view = {
        "exists": log_stats.exists,
        "line_count": log_stats.line_count,
        "runtime_seconds": runtime_actual if runtime_actual >= 0 else None,
        "error_lines": log_stats.error_lines,
        "warning_lines": log_stats.warning_lines,
    }

    payload = {
        "generated_at": _now_iso(),
        "run": {
            "health": health,
            "fallback_detected": log_stats.fallback_detected,
            "timeout_detected": log_stats.timeout_detected,
            "protocol_error_detected": log_stats.protocol_error_detected,
        },
        "assessment": assessment,
        "log": log_view,
        "rolling": rolling,
        "slo": {
            "pass": slo_pass,
            "checks": checks,
        },
    }

    history_tail_payload = {
        "generated_at": _now_iso(),
        "window_size": max(1, args.window_size),
        "rows": window_rows,
    }

    output_path = Path(args.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    history_tail_path = Path(args.history_tail_path)
    history_tail_path.parent.mkdir(parents=True, exist_ok=True)
    history_tail_path.write_text(json.dumps(history_tail_payload, indent=2), encoding="utf-8")

    summary_text = build_summary_md(payload)
    summary_path = Path(args.summary_path)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(summary_text, encoding="utf-8")

    emit_github_outputs(payload)
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
