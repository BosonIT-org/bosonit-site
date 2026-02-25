#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import logging
import os
import select
import subprocess
import sys
import time
from dataclasses import replace
from pathlib import Path
from typing import Any

from habitat_models import HabitatImpactAssessment, fallback_assessment, parse_assessment_text
from habitat_policy import PolicyConfig, apply_policy, load_policy, read_changed_files


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


DEFAULT_MODEL = os.getenv("CODEX_WARDEN_MODEL", "gpt-5.3-codex")
DEFAULT_TIMEOUT_SECONDS = _env_int("CODEX_WARDEN_TIMEOUT_SECONDS", 240)
DEFAULT_REQUEST_TIMEOUT_SECONDS = _env_int("CODEX_WARDEN_REQUEST_TIMEOUT_SECONDS", 60)
DEFAULT_RPC_IDLE_TIMEOUT_SECONDS = _env_int("CODEX_WARDEN_RPC_IDLE_TIMEOUT_SECONDS", 5)
DEFAULT_MAX_DIFF_CHARS = _env_int("CODEX_WARDEN_MAX_DIFF_CHARS", 120000)
DEFAULT_LOG_LEVEL = os.getenv("CODEX_WARDEN_LOG_LEVEL", "INFO")
DEFAULT_LOG_PATH = os.getenv("CODEX_WARDEN_LOG_PATH", "")

LOGGER = logging.getLogger("habitat_warden")
ASSESSMENT_REQUIRED_KEYS = {
    "conservation_status_change",
    "critical_habitat_interference",
    "mitigation_plan_verified",
    "invasive_pattern_detection",
    "regulatory_verdict",
}


def configure_logging(level_name: str, log_path: str) -> None:
    level = getattr(logging, (level_name or "INFO").upper(), logging.INFO)
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stderr)]
    if log_path:
        handlers.append(logging.FileHandler(log_path, encoding="utf-8"))
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
    )


def build_jsonrpc_request(request_id: int, method: str, params: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}


class AppServerClient:
    def __init__(
        self,
        request_timeout_seconds: int,
        rpc_idle_timeout_seconds: int,
    ) -> None:
        self.request_timeout_seconds = request_timeout_seconds
        self.rpc_idle_timeout_seconds = max(1, rpc_idle_timeout_seconds)
        self.proc: subprocess.Popen[bytes] | None = None
        self._next_id = 1
        self._responses: dict[int, dict[str, Any]] = {}
        self._pending_messages: list[dict[str, Any]] = []
        self._stdout_buffer = bytearray()

    def __enter__(self) -> "AppServerClient":
        LOGGER.info("Starting codex app-server over stdio transport.")
        self.proc = subprocess.Popen(
            ["codex", "app-server", "--listen", "stdio://"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if self.proc.stdout:
            os.set_blocking(self.proc.stdout.fileno(), False)
        if self.proc.stderr:
            os.set_blocking(self.proc.stderr.fileno(), False)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if not self.proc:
            return
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait(timeout=2)
        LOGGER.info("codex app-server stopped.")

    def _assert_proc(self) -> subprocess.Popen[bytes]:
        if not self.proc or not self.proc.stdin or not self.proc.stdout:
            raise RuntimeError("Codex app-server process is not initialized.")
        return self.proc

    def _read_stderr_tail(self) -> str:
        proc = self.proc
        if not proc or not proc.stderr:
            return ""
        try:
            chunks: list[bytes] = []
            while True:
                chunk = os.read(proc.stderr.fileno(), 2048)
                if not chunk:
                    break
                chunks.append(chunk)
                if sum(len(c) for c in chunks) >= 8192:
                    break
            if chunks:
                return b"".join(chunks).decode("utf-8", errors="replace")
        except BlockingIOError:
            return ""
        except Exception:
            return ""
        return ""

    def _drain_stdout_messages(self) -> list[dict[str, Any]]:
        proc = self._assert_proc()
        messages: list[dict[str, Any]] = []
        while True:
            try:
                chunk = os.read(proc.stdout.fileno(), 65536)
            except BlockingIOError:
                break
            if not chunk:
                break
            self._stdout_buffer.extend(chunk)

        while True:
            newline_idx = self._stdout_buffer.find(b"\n")
            if newline_idx < 0:
                break
            line = bytes(self._stdout_buffer[:newline_idx])
            del self._stdout_buffer[: newline_idx + 1]

            raw = line.decode("utf-8", errors="replace").strip()
            if not raw:
                continue

            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                LOGGER.debug("Ignoring non-JSON line from app-server stdout.")
                continue

            if isinstance(parsed, dict):
                if LOGGER.isEnabledFor(logging.DEBUG):
                    LOGGER.debug("RPC RECV: %s", self._summarize_payload(parsed))
                messages.append(parsed)

        return messages

    def _send(self, payload: dict[str, Any]) -> None:
        proc = self._assert_proc()
        encoded = (json.dumps(payload, separators=(",", ":")) + "\n").encode("utf-8")
        if LOGGER.isEnabledFor(logging.DEBUG):
            LOGGER.debug("RPC SEND: %s", self._summarize_payload(payload))
        proc.stdin.write(encoded)
        proc.stdin.flush()

    def _summarize_payload(self, payload: dict[str, Any]) -> str:
        if "method" in payload:
            method = payload.get("method")
            params = payload.get("params")
            if isinstance(params, dict):
                hints: list[str] = []
                if "threadId" in params:
                    hints.append(f"threadId={params['threadId']}")
                if "approvalPolicy" in params:
                    hints.append(f"approvalPolicy={params['approvalPolicy']}")
                if "input" in params:
                    hints.append("input=[redacted]")
                if "outputSchema" in params:
                    hints.append("outputSchema=<provided>")
                return f"method={method} " + " ".join(hints)
            return f"method={method}"
        if "id" in payload:
            return f"response id={payload['id']}"
        return "notification"

    def notify(self, method: str, params: dict[str, Any] | None = None) -> None:
        payload: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            payload["params"] = params
        self._send(payload)

    def _read_message(self, timeout_seconds: int) -> dict[str, Any]:
        proc = self._assert_proc()
        deadline = time.time() + timeout_seconds

        while time.time() < deadline:
            if self._pending_messages:
                return self._pending_messages.pop(0)

            if proc.poll() is not None:
                tail = self._read_stderr_tail()
                raise RuntimeError(
                    f"codex app-server exited with code {proc.returncode}. stderr: {tail}"
                )

            remaining = max(0.1, deadline - time.time())
            ready, _, _ = select.select([proc.stdout], [], [], remaining)
            if not ready:
                continue

            self._pending_messages.extend(self._drain_stdout_messages())
            if self._pending_messages:
                return self._pending_messages.pop(0)

        raise TimeoutError("Timed out waiting for JSON-RPC message from codex app-server.")

    def _send_result(self, request_id: Any, result: dict[str, Any]) -> None:
        self._send({"jsonrpc": "2.0", "id": request_id, "result": result})

    def _send_error(self, request_id: Any, message: str, code: int = -32000) -> None:
        self._send({"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}})

    def _handle_server_request(self, message: dict[str, Any]) -> None:
        method = message.get("method")
        request_id = message.get("id")
        LOGGER.warning("Server requested client action via %s; responding conservatively.", method)

        if method in ("item/commandExecution/requestApproval", "item/fileChange/requestApproval"):
            self._send_result(request_id, {"decision": "cancel"})
            return
        if method == "item/tool/requestUserInput":
            self._send_result(request_id, {"answers": {}})
            return
        if method == "item/tool/call":
            self._send_result(
                request_id,
                {
                    "success": False,
                    "contentItems": [
                        {
                            "type": "inputText",
                            "text": "Dynamic tool calls are disabled in warden execution mode.",
                        }
                    ],
                },
            )
            return

        # Legacy request methods; deny conservatively.
        if method in ("execCommandApproval", "applyPatchApproval"):
            self._send_result(request_id, {"decision": "abort"})
            return

        self._send_error(request_id, f"Unsupported server request method: {method}")

    def _dispatch(self, message: dict[str, Any]) -> None:
        if "method" in message and "id" in message:
            self._handle_server_request(message)
            return
        if "id" in message:
            self._responses[int(message["id"])] = message
            return

    def request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        request_id = self._next_id
        self._next_id += 1
        self._send(build_jsonrpc_request(request_id, method, params))
        deadline = time.time() + self.request_timeout_seconds
        last_wait_log = 0.0

        while request_id not in self._responses:
            remaining = deadline - time.time()
            if remaining <= 0:
                tail = self._read_stderr_tail()
                raise TimeoutError(
                    f"Timed out waiting for JSON-RPC response for {method}. stderr: {tail}"
                )
            poll_seconds = min(self.rpc_idle_timeout_seconds, max(1, int(remaining)))
            try:
                incoming = self._read_message(poll_seconds)
            except TimeoutError:
                now = time.time()
                if now - last_wait_log >= 15:
                    LOGGER.info(
                        "Waiting for response to %s (%.0fs remaining).",
                        method,
                        remaining,
                    )
                    last_wait_log = now
                continue
            self._dispatch(incoming)

        response = self._responses.pop(request_id)
        if "error" in response:
            raise RuntimeError(f"JSON-RPC error from app-server: {response['error']}")
        return response

    def wait_for_turn_completion(self, turn_id: str, timeout_seconds: int) -> dict[str, Any]:
        deadline = time.time() + timeout_seconds
        last_wait_log = 0.0
        while time.time() < deadline:
            remaining = deadline - time.time()
            poll_seconds = min(self.rpc_idle_timeout_seconds, max(1, int(remaining)))
            try:
                incoming = self._read_message(poll_seconds)
            except TimeoutError:
                now = time.time()
                if now - last_wait_log >= 15:
                    LOGGER.info(
                        "Waiting for turn %s completion (%.0fs remaining).",
                        turn_id,
                        remaining,
                    )
                    last_wait_log = now
                continue
            method = incoming.get("method")
            params = incoming.get("params") or {}

            if method == "turn/completed":
                turn = params.get("turn") or {}
                if turn.get("id") == turn_id:
                    LOGGER.info("Received turn/completed for turn %s.", turn_id)
                    return turn

            # Some app-server builds stream item completion without a turn/completed event.
            # Treat final agentMessage completion as sufficient signal to proceed.
            if method == "item/completed":
                if params.get("turnId") == turn_id:
                    item = params.get("item") or {}
                    if item.get("type") == "agentMessage":
                        LOGGER.info("Detected agentMessage completion for turn %s.", turn_id)
                        return {"id": turn_id, "status": "completed"}

            self._dispatch(incoming)
        tail = self._read_stderr_tail()
        raise TimeoutError(
            f"Timed out waiting for completion of turn {turn_id} after {timeout_seconds}s. stderr: {tail}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="BosonIT Codex App-Server Habitat Warden")
    parser.add_argument("--diff-path", required=True)
    parser.add_argument("--changed-files-path", required=True)
    parser.add_argument("--policy-path", required=True)
    parser.add_argument("--schema-path", required=True)
    parser.add_argument("--output-path", default="assessment.json")
    parser.add_argument("--cwd", default=os.getcwd())
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument(
        "--request-timeout-seconds",
        type=int,
        default=DEFAULT_REQUEST_TIMEOUT_SECONDS,
    )
    parser.add_argument(
        "--rpc-idle-timeout-seconds",
        type=int,
        default=DEFAULT_RPC_IDLE_TIMEOUT_SECONDS,
    )
    parser.add_argument("--log-level", default=DEFAULT_LOG_LEVEL)
    parser.add_argument("--log-path", default=DEFAULT_LOG_PATH)
    return parser.parse_args()


def read_text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def clip_diff(diff_text: str) -> str:
    if len(diff_text) <= DEFAULT_MAX_DIFF_CHARS:
        return diff_text
    suffix = (
        "\n\n[TRUNCATED_BY_WARDEN]\n"
        f"Original diff length exceeded {DEFAULT_MAX_DIFF_CHARS} characters."
    )
    return diff_text[:DEFAULT_MAX_DIFF_CHARS] + suffix


def build_prompt(diff_text: str, changed_files: list[str], policy: PolicyConfig) -> str:
    changed_lines = "\n".join(f"- {item}" for item in changed_files) if changed_files else "- [none]"
    critical_patterns = "\n".join(f"- {pattern}" for pattern in policy.critical_habitat_regex)

    return (
        "You are the BosonIT Agentic Warden.\n"
        "Return ONLY JSON that matches the provided schema exactly.\n"
        "Do not include markdown, prose, or code fences.\n"
        "Evaluate repository risk from this pull request diff.\n\n"
        "Definitions:\n"
        "- EXTINCTION_LEVEL: catastrophic security or reliability risk.\n"
        "- critical_habitat_interference: true only when critical deploy/infra surface is materially changed.\n"
        "- mitigation_plan_verified: true only when controls/tests/rollback are present in the change context.\n\n"
        "Critical habitat regex in policy:\n"
        f"{critical_patterns}\n\n"
        "Changed files:\n"
        f"{changed_lines}\n\n"
        "Git diff:\n"
        f"{diff_text}\n"
    )


def _collect_text_fragments(value: Any, out: list[str]) -> None:
    if value is None:
        return
    if isinstance(value, str):
        stripped = value.strip()
        if stripped:
            out.append(stripped)
        return
    if isinstance(value, list):
        for item in value:
            _collect_text_fragments(item, out)
        return
    if not isinstance(value, dict):
        return

    preferred_keys = (
        "text",
        "output_text",
        "value",
        "content",
        "message",
        "messages",
        "response",
        "output",
        "result",
    )
    start_len = len(out)
    for key in preferred_keys:
        if key in value:
            _collect_text_fragments(value.get(key), out)

    if len(out) > start_len:
        return

    for nested in value.values():
        _collect_text_fragments(nested, out)
        if len(out) > start_len:
            return


def _extract_text_payload(value: Any) -> str:
    fragments: list[str] = []
    _collect_text_fragments(value, fragments)
    return "\n".join(fragments).strip()


def _iter_nodes(value: Any) -> list[Any]:
    out: list[Any] = []
    stack: list[Any] = [value]
    while stack:
        current = stack.pop()
        out.append(current)
        if isinstance(current, dict):
            for child in current.values():
                stack.append(child)
        elif isinstance(current, list):
            for child in current:
                stack.append(child)
    return out


def _candidate_assessment_dict(node: Any) -> dict[str, Any] | None:
    if not isinstance(node, dict):
        return None
    if ASSESSMENT_REQUIRED_KEYS.issubset(node.keys()):
        return {k: node.get(k) for k in ASSESSMENT_REQUIRED_KEYS}
    nested = node.get("assessment")
    if isinstance(nested, dict) and ASSESSMENT_REQUIRED_KEYS.issubset(nested.keys()):
        return {k: nested.get(k) for k in ASSESSMENT_REQUIRED_KEYS}
    return None


def parse_assessment_from_payload(payload: Any) -> HabitatImpactAssessment:
    validation_errors: list[str] = []

    for node in _iter_nodes(payload):
        candidate = _candidate_assessment_dict(node)
        if candidate is None:
            continue
        try:
            return HabitatImpactAssessment.model_validate(candidate)
        except Exception as exc:
            validation_errors.append(f"dict candidate invalid: {exc}")

    seen_text: set[str] = set()
    for node in _iter_nodes(payload):
        candidate_text = ""
        if isinstance(node, str):
            candidate_text = node.strip()
        elif isinstance(node, (dict, list)):
            candidate_text = _extract_text_payload(node)
        if not candidate_text:
            continue
        if candidate_text in seen_text:
            continue
        seen_text.add(candidate_text)
        if "{" not in candidate_text or "}" not in candidate_text:
            continue
        try:
            return parse_assessment_text(candidate_text)
        except Exception as exc:
            validation_errors.append(f"text candidate invalid: {exc}")

    raise ValueError(
        "No valid structured HabitatImpactAssessment found in payload. "
        f"errors={validation_errors[:3]}"
    )


def parse_assessment_from_thread(thread: dict[str, Any]) -> HabitatImpactAssessment:
    turns = thread.get("turns") or []
    for turn in reversed(turns):
        try:
            return parse_assessment_from_payload(turn)
        except Exception:
            continue
    return parse_assessment_from_payload(thread)


def extract_latest_agent_message(thread: dict[str, Any]) -> str:
    turns = thread.get("turns") or []
    agentish_types = {
        "agentmessage",
        "assistantmessage",
        "assistant",
        "message",
        "outputmessage",
    }
    for turn in reversed(turns):
        for item in reversed(turn.get("items") or []):
            item_type = str(item.get("type", "")).lower()
            role = str(item.get("role", "")).lower()
            should_consider = (
                item_type in agentish_types
                or "assistant" in item_type
                or "agent" in item_type
                or role in {"assistant", "agent"}
                or any(k in item for k in ("text", "content", "message", "messages", "output"))
            )
            if not should_consider:
                continue
            text = _extract_text_payload(item)
            if text:
                return text

        for key in ("output", "response", "result", "message", "messages", "content"):
            if key not in turn:
                continue
            text = _extract_text_payload(turn.get(key))
            if text:
                return text

    for key in ("messages", "items", "message", "output", "response", "result"):
        if key not in thread:
            continue
        text = _extract_text_payload(thread.get(key))
        if text:
            return text

    raise ValueError(
        "No assistant text payload found in thread history. "
        f"thread_keys={sorted(thread.keys())}"
    )


def run_assessment(
    model: str,
    cwd: str,
    turn_timeout_seconds: int,
    request_timeout_seconds: int,
    rpc_idle_timeout_seconds: int,
    prompt: str,
    output_schema: dict[str, Any],
) -> HabitatImpactAssessment:
    with AppServerClient(
        request_timeout_seconds=request_timeout_seconds,
        rpc_idle_timeout_seconds=rpc_idle_timeout_seconds,
    ) as client:
        client.request(
            "initialize",
            {
                "clientInfo": {"name": "bosonit-codex-warden", "version": "1.0.0"},
                "capabilities": {"experimentalApi": True},
            },
        )
        # Follow JSON-RPC lifecycle by notifying server that client initialization is complete.
        client.notify("initialized", {})

        thread_start_params: dict[str, Any] = {
            "approvalPolicy": "never",
            "sandbox": "read-only",
            "cwd": cwd,
            # Needed so thread/read(includeTurns=true) returns turn items including agentMessage.
            "persistExtendedHistory": True,
        }
        if model:
            thread_start_params["model"] = model

        thread_res = client.request("thread/start", thread_start_params)
        thread = (thread_res.get("result") or {}).get("thread") or {}
        thread_id = thread.get("id")
        if not thread_id:
            raise RuntimeError("thread/start returned no thread id.")

        def run_turn(input_text: str) -> tuple[str, Exception | None]:
            turn_res = client.request(
                "turn/start",
                {
                    "threadId": thread_id,
                    "approvalPolicy": "never",
                    "input": [{"type": "text", "text": input_text}],
                    "outputSchema": output_schema,
                },
            )
            turn = (turn_res.get("result") or {}).get("turn") or {}
            turn_id = turn.get("id")
            if not turn_id:
                raise RuntimeError("turn/start returned no turn id.")

            status = turn.get("status")
            wait_error: Exception | None = None
            if status not in ("completed", "failed", "interrupted"):
                try:
                    client.wait_for_turn_completion(turn_id, timeout_seconds=turn_timeout_seconds)
                except Exception as exc:
                    # Keep going with thread/read; some server builds omit completion events.
                    wait_error = exc
                    LOGGER.warning(
                        "Turn completion event wait failed for turn %s; attempting thread/read fallback: %s",
                        turn_id,
                        exc,
                    )
            return turn_id, wait_error

        first_turn_id, wait_error = run_turn(prompt)
        thread_read_res = client.request("thread/read", {"threadId": thread_id, "includeTurns": True})
        full_thread = (thread_read_res.get("result") or {}).get("thread") or {}

        try:
            parsed = parse_assessment_from_thread(full_thread)
            if wait_error is not None:
                LOGGER.info(
                    "Recovered assessment via thread/read after turn wait timeout for turn %s.",
                    first_turn_id,
                )
            return parsed
        except Exception as first_parse_exc:
            LOGGER.warning(
                "Primary structured parse failed for turn %s: %s. Triggering one repair turn.",
                first_turn_id,
                first_parse_exc,
            )
            repair_prompt = (
                "Return ONLY a single JSON object that strictly matches the provided output schema. "
                "Do not include markdown, prose, or code fences. "
                "Re-evaluate the existing thread context and output the final schema object only."
            )
            repair_turn_id, repair_wait_error = run_turn(repair_prompt)
            thread_read_res = client.request("thread/read", {"threadId": thread_id, "includeTurns": True})
            full_thread = (thread_read_res.get("result") or {}).get("thread") or {}
            parsed = parse_assessment_from_thread(full_thread)
            if repair_wait_error is not None:
                LOGGER.info(
                    "Recovered assessment via thread/read after repair turn wait timeout for turn %s.",
                    repair_turn_id,
                )
            return parsed


def _append_multiline_output(path: str, key: str, value: str) -> None:
    marker = "__WARDEN_EOF__"
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"{key}<<{marker}\n{value}\n{marker}\n")


def emit_github_outputs(
    assessment_json: str,
    policy_mode: str,
    final_verdict: str,
    requires_approval: bool,
    denial_reason: str,
    should_block: bool,
) -> None:
    output_path = os.getenv("GITHUB_OUTPUT")
    if output_path:
        with open(output_path, "a", encoding="utf-8") as f:
            f.write(f"policy_mode={policy_mode}\n")
            f.write(f"regulatory_verdict={final_verdict}\n")
            f.write(f"requires_approval={'true' if requires_approval else 'false'}\n")
            f.write(f"should_block={'true' if should_block else 'false'}\n")
            f.write(f"denial_reason={denial_reason}\n")
        _append_multiline_output(output_path, "assessment_json", assessment_json)

    summary_path = os.getenv("GITHUB_STEP_SUMMARY")
    if summary_path:
        summary = (
            "## Habitat Warden Result\n\n"
            f"- Policy mode: `{policy_mode}`\n"
            f"- Final verdict: `{final_verdict}`\n"
            f"- Requires approval: `{str(requires_approval).lower()}`\n"
            f"- Should block: `{str(should_block).lower()}`\n"
            f"- Denial reason: `{denial_reason or 'n/a'}`\n\n"
            "<details><summary>Assessment JSON</summary>\n\n"
            "```json\n"
            f"{assessment_json}\n"
            "```\n"
            "</details>\n"
        )
        with open(summary_path, "a", encoding="utf-8") as f:
            f.write(summary)


def main() -> int:
    args = parse_args()
    configure_logging(level_name=args.log_level, log_path=args.log_path)
    LOGGER.info(
        "Starting Habitat Warden run (model=%s turn_timeout=%ss request_timeout=%ss idle_timeout=%ss).",
        args.model,
        args.timeout_seconds,
        args.request_timeout_seconds,
        args.rpc_idle_timeout_seconds,
    )

    policy = load_policy(args.policy_path)
    mode_override = os.getenv("WARDEN_ENFORCEMENT_MODE", "").strip().lower()
    if mode_override in {"advisory", "enforce"}:
        policy = replace(policy, mode=mode_override)

    changed_files = read_changed_files(args.changed_files_path)
    diff_text = clip_diff(read_text(args.diff_path))
    schema = json.loads(read_text(args.schema_path))

    failure_reason = ""
    try:
        prompt = build_prompt(diff_text=diff_text, changed_files=changed_files, policy=policy)
        assessment = run_assessment(
            model=args.model,
            cwd=args.cwd,
            turn_timeout_seconds=args.timeout_seconds,
            request_timeout_seconds=args.request_timeout_seconds,
            rpc_idle_timeout_seconds=args.rpc_idle_timeout_seconds,
            prompt=prompt,
            output_schema=schema,
        )
    except Exception as exc:
        failure_reason = str(exc)
        LOGGER.exception("Assessment failed; using fail-safe fallback assessment.")
        assessment = fallback_assessment()

    decision = apply_policy(assessment=assessment, changed_files=changed_files, policy=policy)

    if failure_reason and decision.final_verdict != decision.final_verdict.DENY:
        # Preserve fail-safe behavior visibility in CI summary.
        decision = replace(
            decision,
            reasons=decision.reasons + [f"Fail-safe triggered: {failure_reason}"],
        )

    result_payload = {
        "assessment": assessment.model_dump(),
        "policy_mode": policy.mode,
        "final_verdict": decision.final_verdict.value,
        "requires_approval": decision.requires_approval,
        "critical_habitat_touched": decision.critical_habitat_touched,
        "should_block": decision.should_block,
        "denial_reason": decision.denial_reason,
        "reasons": decision.reasons,
    }

    output_json = json.dumps(result_payload, indent=2)
    Path(args.output_path).write_text(output_json + "\n", encoding="utf-8")

    emit_github_outputs(
        assessment_json=output_json,
        policy_mode=policy.mode,
        final_verdict=decision.final_verdict.value,
        requires_approval=decision.requires_approval,
        denial_reason=decision.denial_reason,
        should_block=decision.should_block,
    )
    LOGGER.info(
        "Habitat Warden completed with verdict=%s should_block=%s requires_approval=%s",
        decision.final_verdict.value,
        decision.should_block,
        decision.requires_approval,
    )

    if decision.should_block:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
