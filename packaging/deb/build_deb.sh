#!/usr/bin/env bash
# Builds dist/mysql-db-manager_<version>_<arch>.deb
#
#   1. PyInstaller turns main.py into one binary (dist/MySQLDBManager).
#   2. That binary is laid out as a Debian package tree and packed with dpkg-deb.
#
# Run on an Ubuntu/Debian machine with the project venv active:
#   source .venv/bin/activate
#   pip install pyinstaller
#   packaging/deb/build_deb.sh
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
cd "$ROOT"

PKG_NAME="mysql-db-manager"
APP_BIN="MySQLDBManager"   # PyInstaller output name, same as the README
VERSION="$(tr -d '[:space:]' < VERSION)"
ARCH="$(dpkg --print-architecture)"
STAGE="build/deb/${PKG_NAME}_${VERSION}_${ARCH}"
OUT="dist/${PKG_NAME}_${VERSION}_${ARCH}.deb"

command -v pyinstaller >/dev/null || { echo "pyinstaller not found. Activate .venv and run: pip install pyinstaller" >&2; exit 1; }
command -v dpkg-deb >/dev/null || { echo "dpkg-deb not found. It ships with dpkg on Ubuntu/Debian." >&2; exit 1; }

echo "==> Building ${APP_BIN} with PyInstaller"
pyinstaller --noconfirm --onefile --windowed --name "$APP_BIN" --specpath build main.py

echo "==> Laying out package tree in ${STAGE}"
rm -rf "$STAGE"
install -d "$STAGE/DEBIAN" \
           "$STAGE/usr/bin" \
           "$STAGE/usr/share/applications" \
           "$STAGE/usr/share/doc/$PKG_NAME"
install -m 755 "dist/$APP_BIN" "$STAGE/usr/bin/$PKG_NAME"
install -m 644 "$HERE/$PKG_NAME.desktop" "$STAGE/usr/share/applications/$PKG_NAME.desktop"
install -m 644 LICENSE "$STAGE/usr/share/doc/$PKG_NAME/copyright"

INSTALLED_SIZE="$(du -sk "$STAGE/usr" | cut -f1)"
sed -e "s/@VERSION@/$VERSION/" \
    -e "s/@ARCH@/$ARCH/" \
    -e "s/@INSTALLED_SIZE@/$INSTALLED_SIZE/" \
    "$HERE/control.in" > "$STAGE/DEBIAN/control"

echo "==> Building ${OUT}"
dpkg-deb --build --root-owner-group "$STAGE" "$OUT"

echo
echo "Done: $OUT"
echo "Install with: sudo apt install ./$OUT"
