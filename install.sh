#!/usr/bin/env bash
# hermes-patches installer
# Hermes Agent 体验增强补丁管理、零配置初始化与自动化守护脚本
# Repository: https://github.com/shali10/hermes-patches

set -eo pipefail

BOLD='\033[1m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

# Multi-stage adaptive detection for active Hermes install directory
detect_hermes_dir() {
    # 1. Environment variables
    for ev in "$HERMES_PATCH_SOURCE_ROOT" "$HERMES_SOURCE_DIR" "$HERMES_DIR" "$HERMES_HOME"; do
        if [ -n "$ev" ] && [ -d "$ev" ] && [ -f "$ev/hermes_state.py" ]; then
            echo "$ev"
            return 0
        fi
    done

    # 2. Check running processes
    local running_py
    running_py=$(ps -eo command 2>/dev/null | grep -E "(hermes_cli|gateway\.run|run_agent\.py)" | grep -v grep | awk '{print $1}' | head -n 1 || true)
    if [ -n "$running_py" ] && [ -x "$running_py" ]; then
        local p_cand
        p_cand=$("$running_py" -c "import hermes_state, os; print(os.path.dirname(os.path.abspath(hermes_state.__file__)))" 2>/dev/null || true)
        if [ -n "$p_cand" ] && [ -d "$p_cand" ] && [ -f "$p_cand/hermes_state.py" ]; then
            echo "$p_cand"
            return 0
        fi
    fi

    # 3. Check systemd service ExecStart
    if command -v systemctl >/dev/null 2>&1; then
        local sys_exec
        sys_exec=$(systemctl show hermes-gateway --property=ExecStart 2>/dev/null | grep -o 'path=[^ ;]*' | cut -d= -f2 || true)
        if [ -n "$sys_exec" ] && [ -x "$sys_exec" ]; then
            local s_cand
            s_cand=$("$sys_exec" -c "import hermes_state, os; print(os.path.dirname(os.path.abspath(hermes_state.__file__)))" 2>/dev/null || true)
            if [ -n "$s_cand" ] && [ -d "$s_cand" ] && [ -f "$s_cand/hermes_state.py" ]; then
                echo "$s_cand"
                return 0
            fi
        fi
    fi

    # 4. Probe via `which hermes` shebang & binary path
    if command -v hermes >/dev/null 2>&1; then
        local h_bin
        h_bin=$(readlink -f "$(command -v hermes)" 2>/dev/null || true)
        if [ -n "$h_bin" ] && [ -f "$h_bin" ]; then
            local shebang_py
            shebang_py=$(head -n 1 "$h_bin" 2>/dev/null | sed -n 's/^#!//p' | awk '{print $1}' || true)
            if [ -n "$shebang_py" ] && [ -x "$shebang_py" ]; then
                local b_cand
                b_cand=$("$shebang_py" -c "import hermes_state, os; print(os.path.dirname(os.path.abspath(hermes_state.__file__)))" 2>/dev/null || true)
                if [ -n "$b_cand" ] && [ -d "$b_cand" ] && [ -f "$b_cand/hermes_state.py" ]; then
                    echo "$b_cand"
                    return 0
                fi
            fi

            for depth in 1 2 3 4; do
                local h_cand
                h_cand="$(cd "$(dirname "$h_bin")/$(printf '../%.0s' $(seq 1 $depth))" 2>/dev/null && pwd)"
                if [ -d "$h_cand" ] && [ -f "$h_cand/hermes_state.py" ]; then
                    echo "$h_cand"
                    return 0
                fi
            done
        fi
    fi

    # 5. Probing common virtualenvs
    local py_venvs=(
        "/usr/local/lib/hermes-agent/venv/bin/python"
        "/opt/hermes-agent/venv/bin/python"
        "$HOME/.local/share/uv/tools/hermes-agent/bin/python"
        "$HOME/.local/pipx/venvs/hermes-agent/bin/python"
        "$HOME/.hermes/venv/bin/python"
        "$PYTHON_BIN"
    )
    for vpy in "${py_venvs[@]}"; do
        if [ -x "$vpy" ]; then
            local v_cand
            v_cand=$("$vpy" -c "import hermes_state, os; print(os.path.dirname(os.path.abspath(hermes_state.__file__)))" 2>/dev/null || true)
            if [ -n "$v_cand" ] && [ -d "$v_cand" ] && [ -f "$v_cand/hermes_state.py" ]; then
                echo "$v_cand"
                return 0
            fi
        fi
    done

    # 6. Standard system locations
    local candidates=(
        "/usr/local/lib/hermes-agent"
        "/opt/hermes-agent"
        "$HOME/.local/lib/hermes-agent"
        "$HOME/.local/share/hermes-agent"
        "$HOME/.hermes/hermes-agent"
        "/usr/lib/hermes-agent"
        "$HOME/hermes-agent"
    )
    for c in "${candidates[@]}"; do
        if [ -d "$c" ] && [ -f "$c/hermes_state.py" ]; then
            echo "$c"
            return 0
        fi
    done

    echo ""
}

HERMES_DIR="$(detect_hermes_dir)"

if [ -z "$HERMES_DIR" ]; then
    echo -e "${RED}错误: 未能自动检测到 Hermes Agent 安装目录。${NC}"
    echo -e "请通过环境变量手动指定: ${BOLD}HERMES_SOURCE_DIR=/path/to/hermes-agent bash install.sh${NC}"
    exit 1
fi

# Detect best available Python interpreter (prefer Hermes venv with all dependencies)
PYTHON_BIN=""
if [ -x "$HERMES_DIR/venv/bin/python" ]; then
    PYTHON_BIN="$HERMES_DIR/venv/bin/python"
elif [ -x "/usr/local/lib/hermes-agent/venv/bin/python" ]; then
    PYTHON_BIN="/usr/local/lib/hermes-agent/venv/bin/python"
elif [ -x "/opt/hermes-agent/venv/bin/python" ]; then
    PYTHON_BIN="/opt/hermes-agent/venv/bin/python"
elif [ -x "$HOME/.hermes/venv/bin/python" ]; then
    PYTHON_BIN="$HOME/.hermes/venv/bin/python"
else
    PYTHON_BIN="$(which python3 || which python || true)"
fi

if [ -z "$PYTHON_BIN" ] || [ ! -x "$PYTHON_BIN" ]; then
    echo -e "${RED}错误: 未找到可用的 Python 运行环境。${NC}"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || echo "")"
PATCH_SCRIPT="${SCRIPT_DIR}/hermes_patches.py"

# If running directly from curl pipe or standalone script missing, download to temp
if [ ! -f "$PATCH_SCRIPT" ]; then
    TEMP_DIR=$(mktemp -d)
    trap 'rm -rf "$TEMP_DIR"' EXIT
    curl -fsSL "https://raw.githubusercontent.com/shali10/hermes-patches/main/hermes_patches.py?nocache=$(date +%s)" -o "$TEMP_DIR/hermes_patches.py"
    PATCH_SCRIPT="$TEMP_DIR/hermes_patches.py"
fi

# Function to perform clean uninstallation
do_uninstall() {
    echo -e "\n${YELLOW}正在恢复原始备份文件 (*.bak)...${NC}"
    find "$HERMES_DIR" -name "*.bak" | while read -r bak; do
        orig="${bak%.bak}"
        mv -f "$bak" "$orig"
        echo -e "  • 还原文件: ${CYAN}$orig${NC}"
    done
    
    # Purge __pycache__
    find "$HERMES_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

    if [ -f /etc/systemd/system/hermes-gateway.service.d/10-local-patches.conf ]; then
        rm -f /etc/systemd/system/hermes-gateway.service.d/10-local-patches.conf
        if command -v systemctl >/dev/null 2>&1; then
            systemctl daemon-reload || true
        fi
        echo -e "  • 清理 systemd 守护配置"
    fi

    if [ -f "$HOME/.hermes/scripts/hermes-local-patches.py" ]; then
        rm -f "$HOME/.hermes/scripts/hermes-local-patches.py"
        echo -e "  • 清理 $HOME/.hermes/scripts/hermes-local-patches.py"
    fi

    if command -v systemctl >/dev/null 2>&1 && systemctl is-active --quiet hermes-gateway 2>/dev/null; then
        echo -e "  • 正在重启服务以完成还原..."
        systemctl restart hermes-gateway || true
    fi

    echo -e "\n${GREEN}✓ 卸载与无损回滚完成。${NC}"
    exit 0
}

# Check for --uninstall / -u in CLI args
for arg in "$@"; do
    if [ "$arg" == "--uninstall" ] || [ "$arg" == "-u" ]; then
        do_uninstall
    fi
done

# Function to setup systemd auto-healing hook
setup_systemd_hook() {
    if command -v systemctl >/dev/null 2>&1 && (systemctl list-unit-files 2>/dev/null | grep -q "hermes-gateway.service" || systemctl status hermes-gateway >/dev/null 2>&1); then
        mkdir -p "$HOME/.hermes/scripts"
        cp -f "$PATCH_SCRIPT" "$HOME/.hermes/scripts/hermes-local-patches.py"
        chmod +x "$HOME/.hermes/scripts/hermes-local-patches.py"

        if [ -w "/etc/systemd/system" ] || [ "$EUID" -eq 0 ]; then
            mkdir -p /etc/systemd/system/hermes-gateway.service.d
            cat <<EOF > /etc/systemd/system/hermes-gateway.service.d/10-local-patches.conf
[Service]
Environment="HERMES_PATCH_SOURCE_ROOT=${HERMES_DIR}"
Environment="HERMES_SOURCE_DIR=${HERMES_DIR}"
ExecStartPre=-/usr/bin/env python3 $HOME/.hermes/scripts/hermes-local-patches.py --target ${HERMES_DIR}
EOF
            systemctl reset-failed hermes-gateway 2>/dev/null || true
            systemctl daemon-reload 2>/dev/null || true
            echo -e "${GREEN}✓ 升级自愈守护已就绪 (/etc/systemd/system/hermes-gateway.service.d/10-local-patches.conf)${NC}"
        fi
    fi
}

# 守护进程状态探测与热重载提示
detect_and_report_daemon() {
    echo -e "${BOLD}${CYAN}-----------------------------------------------------${NC}"
    echo -e "${BOLD}📡 网关守护状态探测与热重载诊断：${NC}"

    local is_systemd=false
    if command -v systemctl >/dev/null 2>&1 && systemctl status hermes-gateway >/dev/null 2>&1; then
        is_systemd=true
        local svc_active
        svc_active=$(systemctl is-active hermes-gateway 2>/dev/null || echo "unknown")
        if [ "$svc_active" = "active" ]; then
            echo -e "  • Systemd 服务: ${GREEN}hermes-gateway.service 正在运行中 (active)${NC}"
        else
            echo -e "  • Systemd 服务: ${YELLOW}hermes-gateway.service 状态: ${svc_active}${NC}"
        fi
    fi

    local proc_count
    proc_count=$(ps -eo pid,command 2>/dev/null | grep -E "(gateway\.run|hermes_cli|run_agent\.py)" | grep -v grep | wc -l || echo 0)
    if [ "$proc_count" -gt 0 ]; then
        echo -e "  • 活跃进程: ${GREEN}检测到 ${proc_count} 个 Hermes 网关/运行进程${NC}"
        echo -e "  • 重载建议: ${BOLD}如当前连接在 Telegram，可直接发送 ${CYAN}/restart${NC}${BOLD} 触发热重载${NC}"
    else
        echo -e "  • 活跃进程: 未检测到正在运行的前台网关进程"
        if [ "$is_systemd" = true ]; then
            echo -e "  • 启动建议: 可执行 ${CYAN}systemctl start hermes-gateway${NC} 启动网关"
        fi
    fi
    echo -e "${BOLD}${CYAN}-----------------------------------------------------${NC}"
}

# If CLI arguments are provided, bypass interactive menu and execute directly
if [ "$#" -gt 0 ]; then
    for arg in "$@"; do
        if [ "$arg" == "--list-patches" ] || [ "$arg" == "-h" ] || [ "$arg" == "--help" ] || [ "$arg" == "--status" ] || [ "$arg" == "-V" ] || [ "$arg" == "--version" ]; then
            "$PYTHON_BIN" "$PATCH_SCRIPT" "$@"
            exit 0
        fi
        if [ "$arg" == "--test" ]; then
            echo -e "${BOLD}${BLUE}=== 运行 hermes-patches 行为断言测试套件 ===${NC}"
            "$PYTHON_BIN" "$SCRIPT_DIR/tests/test_behavior.py" --target "$HERMES_DIR"
            exit 0
        fi
    done

    for arg in "$@"; do
        if [ "$arg" == "--dry-run" ]; then
            echo -e "${BOLD}${BLUE}=== Hermes Agent 体验增强补丁 (hermes-patches) ===${NC}"
            echo -e "${GREEN}✓ 目标 Hermes 目录: ${BOLD}${HERMES_DIR}${NC}\n"
            "$PYTHON_BIN" "$PATCH_SCRIPT" --target "$HERMES_DIR" "$@"
            exit 0
        fi
    done

    echo -e "${BOLD}${BLUE}=== Hermes Agent 体验增强补丁 (hermes-patches) ===${NC}"
    echo -e "${GREEN}✓ 目标 Hermes 目录: ${BOLD}${HERMES_DIR}${NC}\n"
    setup_systemd_hook
    "$PYTHON_BIN" "$PATCH_SCRIPT" --target "$HERMES_DIR" --auto-config --restart "$@"

    echo -e "\n${BOLD}${GREEN}🎉 补丁操作执行完毕！${NC}\n"
    detect_and_report_daemon
    exit 0
fi

# =====================================================
# Status Detection & Interactive Menu (交互式多选菜单与状态透视)
# =====================================================

APPLIED_COUNT=0
TOTAL_COUNT=10
declare -A PATCH_ST=()

detect_patches_status() {
    local json_data
    json_data=$("$PYTHON_BIN" "$PATCH_SCRIPT" --target "$HERMES_DIR" --status --json 2>/dev/null || echo "")
    if [ -n "$json_data" ]; then
        eval "$("$PYTHON_BIN" -c '
import json, sys
try:
    d = json.loads(sys.argv[1])
    applied_cnt = d.get("applied", 0)
    total_cnt = d.get("total", 10)
    print(f"APPLIED_COUNT={applied_cnt}")
    print(f"TOTAL_COUNT={total_cnt}")
    for p in d.get("list", []):
        st = "applied" if p.get("applied") else "pending"
        num = p.get("num")
        pid = p.get("id")
        print(f"PATCH_ST[{num}]=\"{st}\"")
        print(f"PATCH_ST[\"{pid}\"]=\"{st}\"")
except Exception:
    pass
' "$json_data" 2>/dev/null || true)"
    fi
}

get_status_badge() {
    local num="$1"
    local st="${PATCH_ST[$num]:-unknown}"
    if [ "$st" = "applied" ]; then
        echo -e "${GREEN}[已应用 ✓]${NC}"
    elif [ "$st" = "pending" ]; then
        echo -e "${YELLOW}[未应用 -]${NC}"
    else
        echo -e "${CYAN}[待检测]${NC}"
    fi
}

get_patch_name_by_num() {
    case "$1" in
        2) echo "📊 Runtime Footer (Token 全量计量、缓存与耗时)" ;;
        3) echo "📑 Telegram CJK 原生 Markdown 表格放行" ;;
        4) echo "🇨🇳 Telegram 快捷菜单与 /help /commands 全中文汉化" ;;
        5) echo "🛡️ SQLite 生产级外键自愈与高并发防锁死" ;;
        6) echo "⚡ Tirith 低风险扫描审批免打扰" ;;
        7) echo "🚫 流式输出静默控制与 429 频控防护" ;;
        8) echo "🧠 全链路深度思考过程强力净化" ;;
        9) echo "✂️ Telegram 4096 长消息智能段落切分" ;;
        10) echo "📁 Terminal 失效工作目录自动回退" ;;
        11) echo "🧱 SQLite 主库防误删护栏" ;;
        *) echo "" ;;
    esac
}

map_num_to_patch() {
    case "$1" in
        2) echo "footer" ;;
        3) echo "table" ;;
        4) echo "menu" ;;
        5) echo "db" ;;
        6) echo "tirith" ;;
        7) echo "nostream" ;;
        8) echo "clean-think" ;;
        9) echo "smart-split" ;;
        10) echo "terminal-cwd" ;;
        11) echo "state-guard" ;;
        *) echo "" ;;
    esac
}

parse_selection_tokens() {
    local input="$1"
    local normalized
    normalized=$(echo "$input" | tr ',;+' ' ')
    local -a result_nums=()

    for token in $normalized; do
        if [[ "$token" =~ ^([0-9]+)[-~]([0-9]+)$ ]]; then
            local s="${BASH_REMATCH[1]}"
            local e="${BASH_REMATCH[2]}"
            if [ "$s" -le "$e" ]; then
                for ((i=s; i<=e; i++)); do
                    if [ "$i" -ge 2 ] && [ "$i" -le 11 ]; then
                        result_nums+=("$i")
                    fi
                done
            else
                for ((i=s; i>=e; i--)); do
                    if [ "$i" -ge 2 ] && [ "$i" -le 11 ]; then
                        result_nums+=("$i")
                    fi
                done
            fi
        elif [[ "$token" =~ ^[0-9]+$ ]]; then
            if [ "$token" -ge 2 ] && [ "$token" -le 11 ]; then
                result_nums+=("$token")
            fi
        fi
    done

    if [ "${#result_nums[@]}" -gt 0 ]; then
        printf '%s\n' "${result_nums[@]}" | sort -nu
    fi
}

show_menu() {
    clear 2>/dev/null || true
    echo -e "${BOLD}${CYAN}=====================================================${NC}"
    echo -e "${BOLD}${BLUE}   🛠️  Hermes Agent 体验增强补丁管理套件 (v1.6.1)   ${NC}"
    echo -e "${BOLD}${CYAN}=====================================================${NC}"
    if [ "$APPLIED_COUNT" -gt 0 ] 2>/dev/null; then
        echo -e " 目标路径: ${GREEN}${HERMES_DIR}${NC}  ${BOLD}(补丁状态: ${GREEN}${APPLIED_COUNT}${NC}/${TOTAL_COUNT} 已应用)${NC}\n"
    else
        echo -e " 目标路径: ${GREEN}${HERMES_DIR}${NC}\n"
    fi
    echo -e " ${BOLD}${GREEN}[1]  🚀 全量一键安装、自动配置并平滑重启 (推荐 / 直接回车)${NC}"
    echo -e " ---------------------------------------------------"
    echo -e " [2]  $(get_status_badge 2)  📊 Runtime Footer (Token 全量计量、缓存与耗时)"
    echo -e " [3]  $(get_status_badge 3)  📑 Telegram CJK 原生 Markdown 表格放行"
    echo -e " [4]  $(get_status_badge 4)  🇨🇳 Telegram 快捷菜单与 /help /commands 全中文汉化"
    echo -e " [5]  $(get_status_badge 5)  🛡️ SQLite 生产级外键自愈与高并发防锁死"
    echo -e " [6]  $(get_status_badge 6)  ⚡ Tirith 低风险扫描审批免打扰"
    echo -e " [7]  $(get_status_badge 7)  🚫 流式输出静默控制与 429 频控防护"
    echo -e " [8]  $(get_status_badge 8)  🧠 全链路深度思考过程强力净化"
    echo -e " [9]  $(get_status_badge 9)  ✂️ Telegram 4096 长消息智能段落切分"
    echo -e " [10] $(get_status_badge 10) 📁 Terminal 失效工作目录自动回退"
    echo -e " [11] $(get_status_badge 11) 🧱 SQLite 主库防误删护栏"
    echo -e " ---------------------------------------------------"
    echo -e " [12] 🔍 预览变更 (Dry Run，不写入磁盘)"
    echo -e " [13] ↩️ 卸载补丁并无损还原 (.bak 原生回滚)"
    echo -e " [14] 🧪 运行运行时行为断言测试套件 (Behavior Test)"
    echo -e " [0]  🚪 退出脚本"
    echo -e "${BOLD}${CYAN}=====================================================${NC}"
}

read_prompt() {
    local prompt_msg="$1"
    local var_name="$2"
    local default_val="$3"
    local input_val=""
    if [ -t 0 ]; then
        read -r -p "$prompt_msg" input_val || return 1
    elif [ -c /dev/tty ] 2>/dev/null; then
        read -r -p "$prompt_msg" input_val < /dev/tty 2>/dev/null || return 1
    else
        return 1
    fi
    input_val="${input_val:-$default_val}"
    printf -v "$var_name" '%s' "$input_val"
    return 0
}

# 判断是否具备交互式终端输入能力 (TTY 或 /dev/tty)
IS_INTERACTIVE=false
if [ -t 0 ]; then
    IS_INTERACTIVE=true
elif [ -c /dev/tty ] 2>/dev/null; then
    IS_INTERACTIVE=true
fi

# 非交互式终端环境 (如自动化脚本/容器无 TTY 管道构建)：默认执行全量安装一次后退出
if [ "$IS_INTERACTIVE" = false ]; then
    echo -e "非交互式终端环境，默认执行: [1] 全量一键安装、自动配置并平滑重启\n"
    setup_systemd_hook
    "$PYTHON_BIN" "$PATCH_SCRIPT" --target "$HERMES_DIR" --auto-config --restart --verbose
    echo -e "\n${BOLD}${GREEN}🎉 补丁操作已全部完成并实时生效！${NC}\n"
    detect_and_report_daemon
    exit 0
fi

# 交互式控制台主会话循环 (Main Interactive Menu Loop)
while true; do
    detect_patches_status
    show_menu

    CHOICE=""
    if ! read_prompt "请输入选项编号 (直接多选如 2 3 7、2,3,7 或 2-5) [默认: 1]: " CHOICE "1"; then
        echo -e "\n${YELLOW}已退出操作。${NC}"
        break
    fi

    CHOICE="${CHOICE:-1}"
    echo ""

    case "$CHOICE" in
        0|q|Q|exit)
            echo -e "${YELLOW}已退出操作。${NC}"
            exit 0
            ;;
        1)
            echo -e "${BLUE}正在全量应用所有增强补丁、自动配置并平滑重启...${NC}\n"
            setup_systemd_hook
            "$PYTHON_BIN" "$PATCH_SCRIPT" --target "$HERMES_DIR" --auto-config --restart --verbose
            echo -e "\n${BOLD}${GREEN}🎉 补丁操作已全部完成并实时生效！${NC}\n"
            detect_and_report_daemon
            ;;
        12)
            echo -e "${YELLOW}正在执行 Dry-Run 预检分析...${NC}\n"
            "$PYTHON_BIN" "$PATCH_SCRIPT" --target "$HERMES_DIR" --dry-run --verbose
            ;;
        13)
            do_uninstall
            echo -e "\n${BOLD}${GREEN}🎉 卸载与还原操作已完成！${NC}\n"
            detect_and_report_daemon
            ;;
        14)
            echo -e "${BOLD}${BLUE}=== 运行 hermes-patches 行为断言测试套件 ===${NC}\n"
            TEST_RUNNER="$SCRIPT_DIR/tests/test_behavior.py"
            if [ ! -f "$TEST_RUNNER" ]; then
                t_dir="${TEMP_DIR:-$(mktemp -d)}"
                TEMP_TEST="$t_dir/test_behavior.py"
                curl -fsSL "https://raw.githubusercontent.com/shali10/hermes-patches/main/tests/test_behavior.py?nocache=$(date +%s)" -o "$TEMP_TEST" 2>/dev/null || true
                TEST_RUNNER="$TEMP_TEST"
            fi
            if [ -f "$TEST_RUNNER" ]; then
                "$PYTHON_BIN" "$TEST_RUNNER" --target "$HERMES_DIR"
            else
                echo -e "${RED}无法加载测试套件脚本。${NC}"
            fi
            ;;
        *)
            mapfile -t PARSED_NUMS < <(parse_selection_tokens "$CHOICE")
            if [ "${#PARSED_NUMS[@]}" -eq 0 ]; then
                echo -e "${RED}输入无效或未匹配到任何可用补丁编号。${NC}\n"
            else
                SELECTED_PATCHES=()
                echo -e "${BOLD}${CYAN}-----------------------------------------------------${NC}"
                echo -e "${BOLD}${BLUE}🎯 直接选中以下 ${#PARSED_NUMS[@]} 项补丁开始安装：${NC}"
                for num in "${PARSED_NUMS[@]}"; do
                    p_id=$(map_num_to_patch "$num")
                    if [ -n "$p_id" ]; then
                        SELECTED_PATCHES+=("$p_id")
                        p_name=$(get_patch_name_by_num "$num")
                        s_badge=$(get_status_badge "$num")
                        echo -e "  • [${num}]  ${s_badge}  ${p_name}"
                    fi
                done
                echo -e "${BOLD}${CYAN}-----------------------------------------------------${NC}\n"

                setup_systemd_hook
                "$PYTHON_BIN" "$PATCH_SCRIPT" --target "$HERMES_DIR" --only "${SELECTED_PATCHES[@]}" --auto-config --restart --verbose
                echo -e "\n${BOLD}${GREEN}🎉 补丁操作已全部完成并实时生效！${NC}\n"
                detect_and_report_daemon
            fi
            ;;
    esac

    # 循环底部提示：允许用户按回车刷新并返回主菜单，或输入 0 / q 优雅退出
    echo ""
    NEXT_ACTION=""
    if ! read_prompt "按回车键返回主菜单，或输入 0 退出: " NEXT_ACTION ""; then
        echo -e "\n${YELLOW}已退出操作。${NC}"
        break
    fi

    if [[ "$NEXT_ACTION" =~ ^(0|q|Q|exit)$ ]]; then
        echo -e "${YELLOW}已退出操作。${NC}"
        exit 0
    fi
done
