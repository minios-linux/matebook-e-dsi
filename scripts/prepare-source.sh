#!/usr/bin/env bash
set -euo pipefail
SRC=${1:?Usage: prepare-source.sh /path/to/clean/linux-6.12.107 /output/path}
DEST=${2:?Specify output path}
REPO=$(cd "$(dirname "$0")/.." && pwd)
[[ ! -e "$DEST" ]] || { echo "Destination already exists: $DEST" >&2; exit 1; }
mkdir -p "$DEST/drivers/gpu/drm" "$DEST/drivers/platform/x86"
cp -a "$SRC/drivers/gpu/drm/i915" "$DEST/drivers/gpu/drm/"
cp "$SRC/drivers/platform/x86/intel_ips.h" "$DEST/drivers/platform/x86/"
patch --batch --fuzz=0 -d "$DEST" -p1 < "$REPO/patches/linux-6.12.107.patch"
patch --batch --fuzz=0 -d "$DEST" -p1 < "$REPO/patches/dsi-dsc-1.1-rc-params.patch"
cp "$REPO/Makefile" "$DEST/Makefile"
cp "$REPO/dkms.conf" "$DEST/dkms.conf"
echo 'Prepared MateBook E DSI source for Linux 6.12.107.'
