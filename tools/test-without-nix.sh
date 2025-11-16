#!/usr/bin/env bash
# Test if parakeet-dictation works without nix-shell
# This script should be run OUTSIDE of nix-shell

set -e

echo "🧪 Testing Parakeet Dictation without nix-shell"
echo "================================================"
echo ""

# Check if we're in nix-shell (should NOT be)
if [ -n "$IN_NIX_SHELL" ]; then
    echo "❌ ERROR: You're currently in nix-shell!"
    echo "Please exit nix-shell first and run this script again."
    exit 1
fi

echo "✓ Not in nix-shell (good)"
echo ""

# 1. Check system dependencies
echo "1️⃣  Checking system dependencies..."
echo "-----------------------------------"

check_command() {
    if command -v "$1" &> /dev/null; then
        echo "  ✓ $1: $(command -v $1)"
        return 0
    else
        echo "  ✗ $1: NOT FOUND"
        return 1
    fi
}

check_lib() {
    if ldconfig -p 2>/dev/null | grep -q "$1"; then
        echo "  ✓ lib$1: $(ldconfig -p | grep "$1" | head -n1 | awk '{print $NF}')"
        return 0
    else
        echo "  ✗ lib$1: NOT FOUND"
        return 1
    fi
}

MISSING_DEPS=0

# Required commands
check_command python3 || MISSING_DEPS=$((MISSING_DEPS + 1))
check_command uv || MISSING_DEPS=$((MISSING_DEPS + 1))
check_command wl-copy || echo "  ⚠ wl-copy: NOT FOUND (Wayland clipboard - optional, xclip may work)"
check_command notify-send || echo "  ⚠ notify-send: NOT FOUND (optional, for notifications)"

echo ""

# Required libraries
echo "2️⃣  Checking required libraries..."
echo "-----------------------------------"

check_lib portaudio || MISSING_DEPS=$((MISSING_DEPS + 1))
check_lib asound || MISSING_DEPS=$((MISSING_DEPS + 1))  # alsa-lib
check_lib pulse || echo "  ⚠ libpulse: NOT FOUND (may not be critical)"

echo ""

# 3. Check Python version
echo "3️⃣  Checking Python version..."
echo "-----------------------------------"
python3 --version

echo ""

# 4. Try creating venv with uv
echo "4️⃣  Testing uv venv creation..."
echo "-----------------------------------"

if [ -d ".venv-test" ]; then
    echo "  Removing old test venv..."
    rm -rf .venv-test
fi

if uv venv .venv-test; then
    echo "  ✓ uv venv created successfully"

    # 5. Try installing PyAudio (the most critical dependency)
    echo ""
    echo "5️⃣  Testing PyAudio installation..."
    echo "-----------------------------------"

    if uv pip install --python .venv-test/bin/python pyaudio; then
        echo "  ✓ PyAudio installed successfully"

        # 6. Try importing PyAudio
        echo ""
        echo "6️⃣  Testing PyAudio import..."
        echo "-----------------------------------"

        if .venv-test/bin/python -c "import pyaudio; pa = pyaudio.PyAudio(); print(f'  ✓ PyAudio works! Found {pa.get_device_count()} audio devices'); pa.terminate()"; then
            echo "  ✓ PyAudio import and initialization successful!"
        else
            echo "  ✗ PyAudio import or initialization failed"
            MISSING_DEPS=$((MISSING_DEPS + 1))
        fi
    else
        echo "  ✗ PyAudio installation failed"
        MISSING_DEPS=$((MISSING_DEPS + 1))
    fi

    # Cleanup test venv
    echo ""
    echo "Cleaning up test venv..."
    rm -rf .venv-test
else
    echo "  ✗ uv venv creation failed"
    MISSING_DEPS=$((MISSING_DEPS + 1))
fi

echo ""
echo "================================================"
echo "📊 SUMMARY"
echo "================================================"
echo "Missing dependencies: $MISSING_DEPS"
echo ""

if [ $MISSING_DEPS -eq 0 ]; then
    echo "✅ SUCCESS: All dependencies available!"
    echo ""
    echo "You can likely run parakeet-dictation without nix-shell."
    echo "Next step: Try 'make setup' outside of nix-shell."
    exit 0
else
    echo "❌ FAILED: $MISSING_DEPS critical dependency/dependencies missing"
    echo ""
    echo "To fix, you can either:"
    echo ""
    echo "Option 1: Add to your home.nix (recommended):"
    echo "  home.packages = ["
    echo "    # ... your existing packages ..."
    echo "    pkgs.portaudio"
    echo "    pkgs.alsa-lib"
    echo "    pkgs.libpulseaudio"
    echo "    pkgs.libnotify"
    echo "    # pkgs.wl-clipboard  # you already have this"
    echo "  ];"
    echo ""
    echo "  Then run: home-manager switch"
    echo ""
    echo "Option 2: Install system-wide (if not using NixOS):"
    echo "  Ubuntu/Debian:"
    echo "    sudo apt install portaudio19-dev libasound2-dev libpulse-dev libnotify-bin"
    echo ""
    echo "  Arch:"
    echo "    sudo pacman -S portaudio alsa-lib libpulse libnotify"
    exit 1
fi
