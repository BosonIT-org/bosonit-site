from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from codex_warden_appserver import build_jsonrpc_request  # noqa: E402


def test_build_jsonrpc_request_shape() -> None:
    payload = build_jsonrpc_request(7, "thread/start", {"approvalPolicy": "never"})
    assert payload["jsonrpc"] == "2.0"
    assert payload["id"] == 7
    assert payload["method"] == "thread/start"
    assert payload["params"]["approvalPolicy"] == "never"

