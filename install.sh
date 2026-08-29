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
    echo -e "${RED}Error: python3 not found.${NC}"
    exit 1
fi

# Detect Hermes install directory
detect_hermes_dir() {
    local candidates=(
        "/usr/local/lib/hermes-agent"
        "/opt/hermes-agent"
        "$HOME/.local/lib/hermes-agent"
    )
    for c in "${candidates[@]}"; do
        if [ -d "$c" ] && [ -f "$c/hermes_state.py" ]; then
            echo "$c"
            return 0
        fi
    done

    # Try pip site-packages
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
    echo -e "Please specify manually with: HERMES_SOURCE_DIR=/path/to/hermes-agent bash install.sh"
    exit 1
fi

echo -e "${GREEN}✓ Found Hermes Agent at: ${BOLD}${HERMES_DIR}${NC}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PATCH_SCRIPT="${SCRIPT_DIR}/hermes_patches.py"

# If running directly from curl pipe, download hermes_patches.py to a temp directory
if [ ! -f "$PATCH_SCRIPT" ]; then
    TEMP_DIR=$(mktemp -d)
    trap 'rm -rf "$TEMP_DIR"' EXIT
    curl -fsSL https://raw.githubusercontent.com/shali10/hermes-patches/main/hermes_patches.py -o "$TEMP_DIR/hermes_patches.py"
    PATCH_SCRIPT="$TEMP_DIR/hermes_patches.py"
fi

# Check for --uninstall
if [ "$1" == "--uninstall" ]; then
    echo -e "${YELLOW}Restoring original backup files...${NC}"
    find "$HERMES_DIR" -name "*.bak" | while read -r bak; do
        orig="${bak%.bak}"
        mv -f "$bak" "$orig"
        echo "Restored $orig"
    done
    
    if [ -f /etc/systemd/system/hermes-gateway.service.d/10-local-patches.conf ]; then
        rm -f /etc/systemd/system/hermes-gateway.service.d/10-local-patches.conf
        systemctl daemon-reload
        echo "Removed systemd patch hook."
    fi
    echo -e "${GREEN}✓ Uninstallation complete.${NC}"
    exit 0
fi

# Run patches
echo -e "${BLUE}Applying enhancement patches...${NC}"
"$PYTHON_BIN" "$PATCH_SCRIPT" --target "$HERMES_DIR" -v

# Setup systemd auto-healing hook if gateway service exists
if systemctl list-unit-files | grep -q "hermes-gateway.service"; then
    echo -e "${BLUE}Configuring systemd auto-healing hook...${NC}"
    mkdir -p /root/.hermes/scripts
    cp -f "$PATCH_SCRIPT" /root/.hermes/scripts/hermes-local-patches.py
    chmod +x /root/.hermes/scripts/hermes-local-patches.py

    mkdir -p /etc/systemd/system/hermes-gateway.service.d
    cat <<EOF > /etc/systemd/system/hermes-gateway.service.d/10-local-patches.conf
[Service]
Environment="HERMES_PATCH_SOURCE_ROOT=${HERMES_DIR}"
ExecStartPre=/root/.hermes/scripts/hermes-local-patches.py
EOF
    systemctl daemon-reload
    echo -e "${GREEN}✓ Auto-healing supervision hook configured (ExecStartPre).${NC}"
fi

# Ensure runtime_footer is enabled in config.yaml
CONFIG_PATH="$HOME/.hermes/config.yaml"
if [ -f "$CONFIG_PATH" ]; then
    echo -e "${BLUE}Ensuring runtime_footer fields enabled in config.yaml...${NC}"
    "$PYTHON_BIN" -c '
import yaml, os
cfg_path = os.path.expanduser("~/.hermes/config.yaml")
try:
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    disp = cfg.setdefault("display", {})
    rf = disp.setdefault("runtime_footer", {})
    rf["enabled"] = True
    rf["fields"] = ["model", "prompt_tokens", "cache_read", "output_tokens", "context_pct", "elapsed_time"]
    with open(cfg_path, "w", encoding="utf-8") as f:
        yaml.dump(cfg, f, default_flow_style=False, allow_unicode=True)
    print("✓ config.yaml runtime_footer updated")
except Exception as e:
    print(f"Notice: config.yaml check skipped ({e})")
' 2>/dev/null || true
fi

echo -e "\n${BOLD}${GREEN}🎉 Hermes Patches installed successfully!${NC}"
echo -e "Restart your gateway via Telegram (${BOLD}/restart${NC}) to take effect.\n"
