#!/usr/bin/env bash
# Build SCROOGE.app with PyInstaller + pywebview (macOS).
# Run from any directory: bash /path/to/scrooge/build_macos_app.sh

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="${TOKEN_TELEMETRY_BUILD_VENV:-${ROOT}/.venv-build}"
SPEC="${ROOT}/native_app/SCROOGE.spec"
ICNS_DST="${ROOT}/native_app/SCROOGE.icns"
ICON_SRC="${ROOT}/docs/fr/assets/icon.jpg"
ICONSET="${ROOT}/native_app/SCROOGE.iconset"

log() {
  printf '%s\n' "$*"
}

if [[ "$(uname -s)" != "Darwin" ]]; then
  log "This builder targets macOS only."
  exit 1
fi

if [[ ! -f "${SPEC}" ]]; then
  log "Missing spec: ${SPEC}"
  exit 1
fi

if [[ ! -d "${VENV}" ]]; then
  log "Creating venv: ${VENV}"
  python3 -m venv "${VENV}"
fi

log "Installing build dependencies…"
"${VENV}/bin/pip" install -r "${ROOT}/requirements-native-build.txt"

if [[ -f "${ICON_SRC}" ]]; then
  if [[ ! -f "${ICNS_DST}" ]] || [[ "${ICON_SRC}" -nt "${ICNS_DST}" ]]; then
    log "Building ${ICNS_DST} from icon.jpg…"
    rm -rf "${ICONSET}"
    mkdir -p "${ICONSET}"
    for job in \
      "16:icon_16x16.png" \
      "32:icon_16x16@2x.png" \
      "32:icon_32x32.png" \
      "64:icon_32x32@2x.png" \
      "128:icon_128x128.png" \
      "256:icon_128x128@2x.png" \
      "256:icon_256x256.png" \
      "512:icon_256x256@2x.png" \
      "512:icon_512x512.png" \
      "1024:icon_512x512@2x.png"; do
      z="${job%%:*}"
      f="${job#*:}"
      sips -s format png "${ICON_SRC}" -z "${z}" "${z}" --out "${ICONSET}/${f}" >/dev/null
    done
    if iconutil -c icns "${ICONSET}" -o "${ICNS_DST}" 2>/dev/null; then
      log "Icon ready: ${ICNS_DST}"
    else
      log "iconutil failed (optional); removing partial icns."
      rm -f "${ICNS_DST}"
      log "Build will continue with default executable icon."
    fi
    rm -rf "${ICONSET}"
  else
    log "Reusing existing ${ICNS_DST}"
  fi
else
  log "No icon.jpg at ${ICON_SRC}; app will use default PyInstaller icon."
fi

log "Running PyInstaller…"
cd "${ROOT}"
rm -rf "${HOME}/Library/Application Support/pyinstaller/bincache"* 2>/dev/null || true
"${VENV}/bin/pyinstaller" "${SPEC}" --clean --noconfirm


APP="${ROOT}/dist/SCROOGE.app"
if [[ -d "${APP}" ]]; then
  log "Ad-hoc signing (required for WebKit on recent macOS)…"
  codesign --force --deep --sign - "${APP}" 2>/dev/null || log "codesign failed or unavailable; if the app quits at launch, run: codesign --force --deep --sign - \"${APP}\""
  log "Done: ${APP}"
else
  log "Expected output missing: ${APP}"
  exit 1
fi
