#!/usr/bin/env python3
"""
Runtime behavioral assertion suite for hermes-patches.
Verifies that all 9 patches correctly modify the target Hermes Agent codebase
and produce the expected behavioral changes and signatures.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def detect_target_dir(explicit_target: str = None) -> Path:
    if explicit_target:
        p = Path(explicit_target).resolve()
        if p.is_dir():
            return p

    # 1. Check environment variables
    for env_k in ["HERMES_PATCH_SOURCE_ROOT", "HERMES_AGENT_ROOT", "HERMES_SOURCE_DIR", "HERMES_DIR", "HERMES_HOME"]:
        val = os.environ.get(env_k)
        if val:
            p = Path(val).resolve()
            if p.is_dir() and (p / "hermes_state.py").is_file():
                return p

    # 2. Check running processes
    try:
        ps_out = subprocess.check_output(["ps", "-eo", "command"], text=True, errors="ignore")
        for line in ps_out.splitlines():
            if "grep" in line or "test_behavior" in line:
                continue
            if any(k in line for k in ["hermes_cli", "gateway.run", "run_agent.py"]):
                py_bin = line.strip().split()[0]
                cand = subprocess.check_output(
                    [py_bin, "-c", "import hermes_state, os; print(os.path.dirname(os.path.abspath(hermes_state.__file__)))"],
                    text=True, stderr=subprocess.DEVNULL
                ).strip()
                if cand and Path(cand).is_dir() and (Path(cand) / "hermes_state.py").is_file():
                    return Path(cand)
    except Exception:
        pass

    # 3. Standard candidate paths
    candidates = [
        "/usr/local/lib/hermes-agent",
        "/opt/hermes-agent",
        Path.home() / ".local/lib/hermes-agent",
        Path.home() / ".local/share/hermes-agent",
        Path.home() / ".hermes/hermes-agent",
        Path.home() / "hermes-agent",
        "/tmp/hermes-agent",
    ]
    for c in candidates:
        p = Path(c).resolve()
        if p.is_dir() and (p / "hermes_state.py").is_file():
            return p

    tmp_p = Path("/tmp/hermes-agent").resolve()
    if tmp_p.is_dir():
        return tmp_p

    return None


def main():
    parser = argparse.ArgumentParser(description="hermes-patches runtime behavioral assertions")
    parser.add_argument("--target", default=None, help="Path to patched hermes-agent directory (auto-detected if omitted)")
    args = parser.parse_args()

    target_dir = detect_target_dir(args.target)
    if not target_dir or not target_dir.is_dir():
        print(
            "Error: Could not locate a valid hermes-agent directory.\\n"
            "Checked locations: /usr/local/lib/hermes-agent, /opt/hermes-agent, ~/.local/lib/hermes-agent, /tmp/hermes-agent\\n"
            "Please specify the path using --target <path> or export HERMES_PATCH_SOURCE_ROOT=<path>",
            file=sys.stderr,
        )
        sys.exit(1)

    sys.path.insert(0, str(target_dir))

    print(f"Running behavioral assertions against: {target_dir}")

    # -------------------------------------------------------------
    # 1. Runtime Footer
    # -------------------------------------------------------------
    print("Testing 1/10: Runtime Footer...")
    from gateway.runtime_footer import format_runtime_footer
    line = format_runtime_footer(
        model="gemini-3.7-flash-high",
        turn_seconds=2.5,
        context_tokens=10000,
        context_length=1000000,
        prompt_tokens=10000,
        output_tokens=500,
        cache_read_tokens=8000,
        fields=["model", "prompt_tokens", "cache_read", "output_tokens", "context_pct", "elapsed_time"]
    )
    assert "🤖 gemini-3.7-flash-high" in line, f"Missing model in footer: {line}"
    assert "🧠 Prompt总量: 10,000" in line, f"Missing prompt tokens: {line}"
    assert "💾 缓存命中: 8,000 (80%)" in line, f"Missing cache read: {line}"
    assert "📤 输出: 500" in line, f"Missing output tokens: {line}"

    # -------------------------------------------------------------
    # 2. Telegram CJK Table Bypass
    # -------------------------------------------------------------
    print("Testing 2/10: Telegram CJK Table Bypass...")
    from plugins.platforms.telegram.adapter import TelegramAdapter
    adapter = TelegramAdapter.__new__(TelegramAdapter)
    table_sample = "测试表格\n| a | b |\n|---|---|\n| 1 | 2 |"
    assert adapter._has_telegram_desktop_cjk_rich_garble_shape(table_sample) is False
    assert adapter._needs_rich_rendering(table_sample) is True

    # -------------------------------------------------------------
    # 3. Telegram Chinese Commands
    # -------------------------------------------------------------
    print("Testing 3/10: Telegram Chinese Commands...")
    try:
        from hermes_cli.commands_platforms import telegram_bot_commands
    except ImportError:
        from hermes_cli.commands import telegram_bot_commands
    from hermes_cli.commands import gateway_help_lines
    cmds = telegram_bot_commands()
    assert len(cmds) > 0, "No bot commands registered"
    assert any("响应平台启动请求" in d for _, d in cmds), "Chinese command description not found"
    help_lines = gateway_help_lines()
    assert any("响应平台启动请求" in l for l in help_lines), "Chinese help description not found"

    # -------------------------------------------------------------
    # 4. State DB Hardening
    # -------------------------------------------------------------
    print("Testing 4/10: State DB Hardening...")
    state_file = target_dir / "hermes_state.py"
    wal_file = target_dir / "hermes_state_wal.py"
    messages_file = target_dir / "hermes_state_messages.py"

    state_code = state_file.read_text(encoding="utf-8") if state_file.is_file() else ""
    if wal_file.is_file():
        wal_code = wal_file.read_text(encoding="utf-8")
        assert "PRAGMA busy_timeout = 5000" in wal_code or "PRAGMA busy_timeout = 5000" in state_code, "PRAGMA busy_timeout missing"
    else:
        assert "PRAGMA busy_timeout = 5000" in state_code, "PRAGMA busy_timeout missing in hermes_state.py"

    if messages_file.is_file():
        msg_code = messages_file.read_text(encoding="utf-8")
        assert "FK self-heal" in msg_code or "FK self-heal" in state_code, "FK self-heal missing"
    else:
        assert "FK self-heal: ensure the session parent row exists" in state_code, "FK self-heal missing in append_message"
        assert "FK batch self-heal" in state_code, "FK batch self-heal missing in append_messages_batch"

    # -------------------------------------------------------------
    # 5. Tirith Low-Severity
    # -------------------------------------------------------------
    print("Testing 5/10: Tirith Low-Severity Approval...")
    approval_code = (target_dir / "tools/approval.py").read_text(encoding="utf-8")
    assert "_skip_low_warn" in approval_code, "_skip_low_warn missing in tools/approval.py"
    assert 'return {"approved": True, "message": None}' in approval_code, "Dict return contract missing in _skip_low_warn"

    # -------------------------------------------------------------
    # 6. Streaming Control + Gateway cache-read transport
    # -------------------------------------------------------------
    print("Testing 6/10: Streaming Control & Cache Tokens Transport...")
    run_file = target_dir / "gateway/run.py"
    runner_file = target_dir / "gateway/run_turn_runner.py"
    if runner_file.is_file():
        runner_code = runner_file.read_text(encoding="utf-8")
        assert "_global_display_streaming" in runner_code, "_global_display_streaming missing in gateway/run_turn_runner.py"
        assert '"cache_read_tokens": getattr(agent, "session_cache_read_tokens"' in runner_code, "cache_read_tokens missing in usage dict"
    else:
        run_code = run_file.read_text(encoding="utf-8")
        assert "_global_display_streaming" in run_code, "_global_display_streaming missing in gateway/run.py"
        assert run_code.count('"cache_read_tokens": _cache_read_toks') == 2, "cache_read_tokens payload count != 2"
        assert run_code.count('_cache_read_toks = getattr(_agent, "session_cache_read_tokens", 0) or 0') == 1, "_cache_read_toks extraction count != 1"

    # -------------------------------------------------------------
    # 7. Clean Thinking
    # -------------------------------------------------------------
    print("Testing 7/10: Clean Thinking...")
    cli_file = target_dir / "cli.py"
    stream_file = target_dir / "gateway/stream_consumer.py"
    cli_mixin = target_dir / "hermes_cli/cli_stream_mixin.py"
    stream_think = target_dir / "gateway/stream_consumer_think.py"

    cli_code = cli_mixin.read_text(encoding="utf-8") if cli_mixin.is_file() else cli_file.read_text(encoding="utf-8")
    stream_code = stream_think.read_text(encoding="utf-8") if stream_think.is_file() else stream_file.read_text(encoding="utf-8")
    assert "<antml:thought>" in cli_code and "<antml:thought>" in stream_code, "Thought tags missing in clean-thinking"

    # -------------------------------------------------------------
    # 8. Telegram 4096 Smart Split
    # -------------------------------------------------------------
    print("Testing 8/10: Telegram 4096 Smart Split...")
    base_code = (target_dir / "gateway/platforms/base.py").read_text(encoding="utf-8")
    assert "hermes-patches smart-split" in base_code, "smart-split missing in gateway/platforms/base.py"

    # -------------------------------------------------------------
    # 9. Terminal CWD Recovery
    # -------------------------------------------------------------
    print("Testing 9/10: Terminal CWD Recovery...")
    env_base_code = (target_dir / "tools/environments/base.py").read_text(encoding="utf-8")
    assert "_resolve_safe_cwd" in env_base_code, "Safe cwd recovery missing in tools/environments/base.py"

    # -------------------------------------------------------------
    # 10. State DB Anti-Destruction Guard
    # -------------------------------------------------------------
    print("Testing 10/10: State DB Anti-Destruction Guard...")
    app_file = target_dir / "tools/approval.py"
    app_detect_file = target_dir / "tools/approval_detection.py"
    approval_full_code = app_detect_file.read_text(encoding="utf-8") if app_detect_file.is_file() else app_file.read_text(encoding="utf-8")
    assert "hermes-patches state-guard" in approval_full_code, "state-guard pattern missing in approval module"
    from tools.approval import detect_hardline_command
    # Dangerous commands targeting live state.db must be blocked unconditionally
    is_blocked, desc = detect_hardline_command("rm /root/.hermes/state.db")
    assert is_blocked, "rm state.db should be hardline-blocked"
    assert "state.db" in str(desc), f"Unexpected description: {desc}"

    is_blocked, desc = detect_hardline_command("truncate -s 0 ~/.hermes/state.db")
    assert is_blocked, "truncate state.db should be hardline-blocked"

    is_blocked, desc = detect_hardline_command("find /root/.hermes -name 'state.db' -delete")
    assert is_blocked, "find-delete state.db should be hardline-blocked"

    # Safe operations must NOT be blocked
    is_blocked, desc = detect_hardline_command("sqlite3 /root/.hermes/state.db 'PRAGMA quick_check;'")
    assert not is_blocked, f"sqlite3 read should NOT be hardline-blocked, got {desc}"

    is_blocked, desc = detect_hardline_command("rm /root/.hermes/backups/state.db.bak")
    assert not is_blocked, f"rm state.db.bak should NOT be hardline-blocked, got {desc}"

    print("\n✅ All 10 patches successfully passed runtime behavioral assertions!")


if __name__ == "__main__":
    main()
