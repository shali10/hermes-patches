#!/usr/bin/env bash
# hermes-patches installer
# One-line installer and auto-healing supervision setup for Hermes Agent.
# Repository: https://github.com/shali10/hermes-patches

set -eo pipefail

BOLD='\033[1m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BOLD}${BLUE}=== Hermes Agent Enhancement Patches (hermes-patches) ===${NC}"

# Detect Python
PYTHON_BIN="$(which python3 || which python || true)"
if [ -z "$PYTHON_BIN" ]; then
    echo -e "${RED}Error: python3 not found in PATH.${NC}"
    exit 1
fi

# Detect Hermes install directory
detect_hermes_dir() {
    if [ -n "$HERMES_SOURCE_DIR" ] && [ -d "$HERMES_SOURCE_DIR" ] && [ -f "$HERMES_SOURCE_DIR/hermes_state.py" ]; then
        echo "$HERMES_SOURCE_DIR"
        return 0
    fi

    # 1. Probe via `which hermes` CLI path resolution
    if command -v hermes >/dev/null 2>&1; then
        local h_bin
        h_bin=$(readlink -f "$(command -v hermes)" 2>/dev/null || true)
        if [ -n "$h_bin" ]; then
            for depth in 1 2 3; do
                local h_cand
                h_cand="$(cd "$(dirname "$h_bin")/$(printf '../%.0s' $(seq 1 $depth))" 2>/dev/null && pwd)"
                if [ -d "$h_cand" ] && [ -f "$h_cand/hermes_state.py" ]; then
                    echo "$h_cand"
                    return 0
                fi
            done
        fi
    fi

    # 2. Standard system locations
    local candidates=(
        "/usr/local/lib/hermes-agent"
        "/opt/hermes-agent"
        "$HOME/.local/lib/hermes-agent"
        "/usr/lib/hermes-agent"
    )
    for c in "${candidates[@]}"; do
        if [ -d "$c" ] && [ -f "$c/hermes_state.py" ]; then
            echo "$c"
            return 0
        fi
    done

    # 3. Pip site-packages probing
    local site_pkg
    site_pkg=$("$PYTHON_BIN" -c "import sys, site; print(site.getsitepackages()[0] if site.getsitepackages() else '')" 2>/dev/null || true)
    if [ -n "$site_pkg" ] && [ -f "$site_pkg/hermes_state.py" ]; then
        echo "$site_pkg"
        return 0
    fi

    echo ""
}

HERMES_DIR="$(detect_hermes_dir)"

if [ -z "$HERMES_DIR" ]; then
    echo -e "${RED}Error: Could not locate Hermes Agent installation directory.${NC}"
    echo -e "Please specify manually with: ${BOLD}HERMES_SOURCE_DIR=/path/to/hermes-agent bash install.sh${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Found Hermes Agent at: ${BOLD}${HERMES_DIR}${NC}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || echo "")"
PATCH_SCRIPT="${SCRIPT_DIR}/hermes_patches.py"

# If running directly from curl pipe or standalone script missing, download to temp
if [ ! -f "$PATCH_SCRIPT" ]; then
    TEMP_DIR=$(mktemp -d)
    trap 'rm -rf "$TEMP_DIR"' EXIT
    curl -fsSL https://raw.githubusercontent.com/shali10/hermes-patches/main/hermes_patches.py -o "$TEMP_DIR/hermes_patches.py"
    PATCH_SCRIPT="$TEMP_DIR/hermes_patches.py"
fi

# Check for --uninstall / -u in any argument position
for arg in "$@"; do
    if [ "$arg" == "--uninstall" ] || [ "$arg" == "-u" ]; then
        echo -e "${YELLOW}Restoring original backup files (*.bak)...${NC}"
        find "$HERMES_DIR" -name "*.bak" | while read -r bak; do
            orig="${bak%.bak}"
            mv -f "$bak" "$orig"
            echo "Restored $orig"
        done
        
        if [ -f /etc/systemd/system/hermes-gateway.service.d/10-local-patches.conf ]; then
            rm -f /etc/systemd/system/hermes-gateway.service.d/10-local-patches.conf
            if command -v systemctl >/dev/null 2>&1; then
                systemctl daemon-reload || true
            fi
            echo "Removed systemd patch hook."
        fi

        if [ -f "$HOME/.hermes/scripts/hermes-local-patches.py" ]; then
            rm -f "$HOME/.hermes/scripts/hermes-local-patches.py"
            echo "Cleaned $HOME/.hermes/scripts/hermes-local-patches.py."
        fi

        echo -e "${GREEN}✓ Uninstallation and rollback complete.${NC}"
        exit 0
    fi
done

# Run patches with forwarded arguments
echo -e "${BLUE}Applying enhancement patches...${NC}"
"$PYTHON_BIN" "$PATCH_SCRIPT" --target "$HERMES_DIR" "$@"

# If user only ran with --list-patches or --dry-run, do not touch systemd/config
for arg in "$@"; do
    if [ "$arg" == "--list-patches" ] || [ "$arg" == "--dry-run" ]; then
        exit 0
    fi
done

# Setup systemd auto-healing hook if gateway service exists and systemctl is present
if command -v systemctl >/dev/null 2>&1 && systemctl list-unit-files 2>/dev/null | grep -q "hermes-gateway.service"; then
    echo -e "${BLUE}Configuring systemd auto-healing hook (ExecStartPre)...${NC}"
    mkdir -p "$HOME/.hermes/scripts"
    cp -f "$PATCH_SCRIPT" "$HOME/.hermes/scripts/hermes-local-patches.py"
    chmod +x "$HOME/.hermes/scripts/hermes-local-patches.py"

    if [ -w "/etc/systemd/system" ] || [ "$EUID" -eq 0 ]; then
        mkdir -p /etc/systemd/system/hermes-gateway.service.d
        cat <<EOF > /etc/systemd/system/hermes-gateway.service.d/10-local-patches.conf
[Service]
Environment="HERMES_PATCH_SOURCE_ROOT=${HERMES_DIR}"
ExecStartPre=$HOME/.hermes/scripts/hermes-local-patches.py
EOF
        systemctl daemon-reload || true
        echo -e "${GREEN}✓ Auto-healing supervision hook configured (/etc/systemd/system/hermes-gateway.service.d/10-local-patches.conf).${NC}"
    else
        echo -e "${YELLOW}Notice: No write permission to /etc/systemd/system. Skipped systemd hook setup (Run with sudo to enable).${NC}"
    fi
else
    echo -e "${YELLOW}Notice: hermes-gateway.service not registered in systemd. Skipped systemd hook setup (Container/CLI mode).${NC}"
fi

echo -e "\n${BOLD}${GREEN}🎉 Hermes Patches applied successfully!${NC}"
echo -e "Restart your gateway via Telegram (${BOLD}/restart${NC}) or systemctl to take effect.\n"
