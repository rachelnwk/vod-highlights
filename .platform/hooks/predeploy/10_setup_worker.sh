#!/bin/bash

set -euo pipefail

APP_STAGING_DIR="/var/app/staging"
WORKER_DIR="$APP_STAGING_DIR/worker"
WORKER_VENV_DIR="${WORKER_VENV_DIR:-/var/worker-venv}"
WORKER_SWAPFILE="${WORKER_SWAPFILE:-/var/worker-swapfile}"
WORKER_SWAP_SIZE_MB="${WORKER_SWAP_SIZE_MB:-2048}"
WORKER_PIP_TMP_DIR="${WORKER_PIP_TMP_DIR:-/var/worker-pip-tmp}"
LEGACY_WORKER_VENV_DIR="/var/app/worker-venv"
LEGACY_WORKER_SWAPFILE="/var/app/worker-swapfile"
LEGACY_WORKER_PIP_TMP_DIR="/var/app/worker-pip-tmp"
export PIP_DISABLE_PIP_VERSION_CHECK=1

cleanup_failed_venv() {
  rm -rf "$WORKER_VENV_DIR"
  rm -rf "$WORKER_PIP_TMP_DIR"
}

trap cleanup_failed_venv ERR

ensure_swap() {
  if swapon --show=NAME --noheadings | grep -qx "$WORKER_SWAPFILE"; then
    return
  fi

  if [[ ! -f "$WORKER_SWAPFILE" ]]; then
    if command -v fallocate >/dev/null 2>&1; then
      fallocate -l "${WORKER_SWAP_SIZE_MB}M" "$WORKER_SWAPFILE"
    else
      dd if=/dev/zero of="$WORKER_SWAPFILE" bs=1M count="$WORKER_SWAP_SIZE_MB" status=none
    fi

    chmod 600 "$WORKER_SWAPFILE"
    mkswap "$WORKER_SWAPFILE" >/dev/null
  fi

  swapon "$WORKER_SWAPFILE"

  if ! grep -qF "$WORKER_SWAPFILE none swap sw 0 0" /etc/fstab; then
    echo "$WORKER_SWAPFILE none swap sw 0 0" >> /etc/fstab
  fi
}

cleanup_previous_worker_artifacts() {
  if swapon --show=NAME --noheadings | grep -qx "$LEGACY_WORKER_SWAPFILE"; then
    swapoff "$LEGACY_WORKER_SWAPFILE"
  fi

  rm -f "$LEGACY_WORKER_SWAPFILE"
  rm -rf "$LEGACY_WORKER_VENV_DIR" "$LEGACY_WORKER_PIP_TMP_DIR"
  rm -rf "$WORKER_PIP_TMP_DIR"

  find /tmp -maxdepth 1 \
    \( -name "pip-*" -o -name "pip-unpack-*" -o -name "pip-install-*" -o -name "pip-ephem-wheel-cache-*" \) \
    -exec rm -rf {} + 2>/dev/null || true
}

if [[ ! -f "$WORKER_DIR/requirements.txt" ]]; then
  echo "Worker requirements not found at $WORKER_DIR/requirements.txt" >&2
  exit 1
fi

cleanup_previous_worker_artifacts
ensure_swap
rm -rf "$WORKER_VENV_DIR"
python3 -m venv "$WORKER_VENV_DIR"
mkdir -p "$WORKER_PIP_TMP_DIR"
export TMPDIR="$WORKER_PIP_TMP_DIR"

"$WORKER_VENV_DIR/bin/pip" install --no-cache-dir --no-compile --prefer-binary -r "$WORKER_DIR/requirements.txt"

rm -rf "$WORKER_PIP_TMP_DIR"
trap - ERR
