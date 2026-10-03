#!/bin/sh
# Build only: never install, sign, load, unload, or alter persistent settings.
set -eu
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
KDIR=${1:-/lib/modules/$(uname -r)/build}
RELEASE=$(sed -n 's/^#define UTS_RELEASE "\([^"]*\)"/\1/p' "$KDIR/include/generated/utsrelease.h")
case "$RELEASE" in
  7.0.0-34-generic)
    SOURCE="$HERE/kernel-source/sound/usb"
    DETECTED_CC=$(python3 "$HERE/check_headers.py" "$KDIR")
    CC=${CC:-$DETECTED_CC}
    ;;
  6.12.107+deb13-amd64)
    SOURCE="$HERE/kernel-source-debian-6.12/sound/usb"
    CC=${CC:-gcc-14}
    ;;
  *) printf '%s\n' "Unsupported build ABI: $RELEASE" >&2; exit 2;;
esac
[ -s "$KDIR/Module.symvers" ] || { echo 'Missing Module.symvers' >&2; exit 2; }
make -C "$KDIR" M="$SOURCE" CONFIG_DEBUG_INFO_BTF_MODULES= CC="$CC" -j"${JOBS:-2}" modules
printf '%s\n' 'Build finished. Module is unsigned; nothing installed or loaded. Read README.zh-CN.md.'
