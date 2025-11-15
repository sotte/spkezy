{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = with pkgs; [
    # Python
    python311
    uv

    # Audio system dependencies
    portaudio
    alsa-lib
    alsa-plugins
    pulseaudio

    # Clipboard support (Wayland)
    wl-clipboard

    # Build tools that might be needed for Python packages
    gcc
    stdenv.cc.cc.lib
  ];

  shellHook = ''
    echo "🚀 Parakeet Dictation Development Environment"
    echo "============================================="
    echo ""
    echo "Python: $(python3 --version)"
    echo "uv: $(uv --version)"
    echo ""
    echo "Next steps:"
    echo "  make setup    - Create venv and install dependencies (CPU)"
    echo "  make run      - Start dictation"
    echo "  make help     - Show all available commands"
    echo ""

    # Set library path for Python packages that need system libraries
    export LD_LIBRARY_PATH="${pkgs.lib.makeLibraryPath [
      pkgs.stdenv.cc.cc.lib
      pkgs.portaudio
      pkgs.alsa-lib
      pkgs.pulseaudio
    ]}:$LD_LIBRARY_PATH"
  '';
}
