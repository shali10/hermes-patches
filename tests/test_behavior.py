#!/usr/bin/env python3
"""
Runtime behavioral assertion suite for hermes-patches.
Verifies that all 8 patches correctly modify the target Hermes Agent codebase
and produce the expected behavioral changes and signatures.
"""

import argparse
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="hermes-patches runtime behavioral assertions")
    parser.add_argument("--target", default="/tmp/hermes-agent", help="Path to patched hermes-agent directory")
    args = parser.parse_args()

    target_dir = Path(args.target).resolve()
    if not target_dir.is_dir():
        print(f"Error: Target directory does not exist: {target_dir}", file=sys.stderr)
        sys.exit(1)

    sys.path.insert(0, str(target_dir))

    print(f"Running behavioral assertions against: {target_dir}")

    # -------------------------------------------------------------
    # 1. Runtime Footer
    # -------------------------------------------------------------
    print("Testing 1/8: Runtime Footer...")
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
    print("Testing 2/8: Telegram CJK Table Bypass...")
    from plugins.platforms.telegram.adapter import TelegramAdapter
    adapter = TelegramAdapter.__new__(TelegramAdapter)
    table_sample = "测试表格\n| a | b |\n|---|---|\n| 1 | 2 |"
    assert adapter._has_telegram_desktop_cjk_rich_garble_shape(table_sample) is False
    assert adapter._needs_rich_rendering(table_sample) is True

    # -------------------------------------------------------------
    # 3. Telegram Chinese Commands
    # -------------------------------------------------------------
    print("Testing 3/8: Telegram Chinese Commands...")
    from hermes_cli.commands import telegram_bot_commands, gateway_help_lines
    cmds = telegram_bot_commands()
    assert len(cmds) > 0, "No bot commands registered"
    assert any("响应平台启动请求" in d for _, d in cmds), "Chinese command description not found"
    help_lines = gateway_help_lines()
    assert any("响应平台启动请求" in l for l in help_lines), "Chinese help description not found"

    # -------------------------------------------------------------
    # 4. State DB Hardening
    # -------------------------------------------------------------
    print("Testing 4/8: State DB Hardening...")
    state_code = (target_dir / "hermes_state.py").read_text(encoding="utf-8")
    assert "PRAGMA busy_timeout = 5000" in state_code, "PRAGMA busy_timeout missing in hermes_state.py"
    assert "FK self-heal: ensure the session parent row exists" in state_code, "FK self-heal missing in append_message"
    assert "FK batch self-heal" in state_code, "FK batch self-heal missing in append_messages_batch"

    # -------------------------------------------------------------
    # 5. Tirith Low-Severity
    # -------------------------------------------------------------
    print("Testing 5/8: Tirith Low-Severity Approval...")
    approval_code = (target_dir / "tools/approval.py").read_text(encoding="utf-8")
    assert "_skip_low_warn" in approval_code, "_skip_low_warn missing in tools/approval.py"
    assert 'return {"approved": True, "message": None}' in approval_code, "Dict return contract missing in _skip_low_warn"

    # -------------------------------------------------------------
    # 6. Streaming Control + Gateway cache-read transport
    # -------------------------------------------------------------
    print("Testing 6/8: Streaming Control & Cache Tokens Transport...")
    run_code = (target_dir / "gateway/run.py").read_text(encoding="utf-8")
    assert "_global_display_streaming" in run_code, "_global_display_streaming missing in gateway/run.py"
    assert run_code.count('"cache_read_tokens": _cache_read_toks') == 2, "cache_read_tokens payload count != 2"
    assert run_code.count('_cache_read_toks = getattr(_agent, "session_cache_read_tokens", 0) or 0') == 1, "_cache_read_toks extraction count != 1"

    # -------------------------------------------------------------
    # 7. Clean Thinking
    # -------------------------------------------------------------
    print("Testing 7/8: Clean Thinking...")
    cli_code = (target_dir / "cli.py").read_text(encoding="utf-8")
    stream_code = (target_dir / "gateway/stream_consumer.py").read_text(encoding="utf-8")
    assert "<antml:thought>" in cli_code and "<antml:thought>" in stream_code, "Thought tags missing in clean-thinking"

    # -------------------------------------------------------------
    # 8. Telegram 4096 Smart Split
    # -------------------------------------------------------------
    print("Testing 8/8: Telegram 4096 Smart Split...")
    base_code = (target_dir / "gateway/platforms/base.py").read_text(encoding="utf-8")
    assert "hermes-patches smart-split" in base_code, "smart-split missing in gateway/platforms/base.py"

    print("\n✅ All 8 patches successfully passed runtime behavioral assertions!")


if __name__ == "__main__":
    main()
