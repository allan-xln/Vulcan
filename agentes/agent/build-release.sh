#!/usr/bin/env bash
set -euo pipefail

AGENT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPOSITORY_ROOT="$(cd "$AGENT_ROOT/../.." && pwd)"
VERSION="${VERSION:-0.2.0}"
COMMIT_SHA="${COMMIT_SHA:-$(git -C "$REPOSITORY_ROOT" rev-parse --short=12 HEAD)}"
BUILD_TIME="${BUILD_TIME:-$(date -u +%Y-%m-%dT%H:%M:%SZ)}"
DIST_DIR="$AGENT_ROOT/dist"
STAGING_DIR="$DIST_DIR/staging"
GO_BINARY="${GO_BINARY:-$REPOSITORY_ROOT/.tools/go/bin/go}"
WIXL_BINARY="${WIXL_BINARY:-$(command -v wixl || true)}"
WIXL_WXIDIR="${WIXL_WXIDIR:-}"
MSIBUILD_BINARY="${MSIBUILD_BINARY:-$(command -v msibuild || true)}"
WIX_CANDLE="${WIX_CANDLE:-}"
WIX_LIGHT="${WIX_LIGHT:-}"
MONO_BINARY="${MONO_BINARY:-$(command -v mono || true)}"

if [ ! -x "$GO_BINARY" ]; then
  echo "Go toolchain not found at $GO_BINARY" >&2
  exit 1
fi

PORTABLE_MSITOOLS="$REPOSITORY_ROOT/.tools/msitools/usr"
if [ -z "$WIXL_BINARY" ] && [ -x "$PORTABLE_MSITOOLS/bin/wixl" ]; then
  WIXL_BINARY="$PORTABLE_MSITOOLS/bin/wixl"
fi
if [ -z "$MSIBUILD_BINARY" ] && [ -x "$PORTABLE_MSITOOLS/bin/msibuild" ]; then
  MSIBUILD_BINARY="$PORTABLE_MSITOOLS/bin/msibuild"
fi
if [ -z "$WIXL_WXIDIR" ] && [ -d "$PORTABLE_MSITOOLS/share/wixl-0.101/include" ]; then
  WIXL_WXIDIR="$PORTABLE_MSITOOLS/share/wixl-0.101/include"
fi
if [ -f "$PORTABLE_MSITOOLS/lib/x86_64-linux-gnu/libmsi.so.0" ]; then
  export LD_LIBRARY_PATH="$PORTABLE_MSITOOLS/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
fi

case "$VERSION" in
  *[!0-9.]*|'')
    echo "VERSION must be numeric for MSI/DEB, for example 0.2.0" >&2
    exit 1
    ;;
esac

mkdir -p "$DIST_DIR" "$STAGING_DIR"
rm -rf "$STAGING_DIR/linux-amd64"
mkdir -p "$STAGING_DIR/linux-amd64/DEBIAN"
mkdir -p "$STAGING_DIR/linux-amd64/usr/bin"
mkdir -p "$STAGING_DIR/linux-amd64/lib/systemd/system"
mkdir -p "$STAGING_DIR/linux-amd64/usr/lib/systemd/user"

LDFLAGS="-s -w -X main.version=$VERSION -X main.commitSHA=$COMMIT_SHA -X main.buildTime=$BUILD_TIME"

(
  cd "$AGENT_ROOT"
  CGO_ENABLED=0 GOOS=linux GOARCH=amd64 "$GO_BINARY" build \
    -trimpath -ldflags "$LDFLAGS" \
    -o "$STAGING_DIR/linux-amd64/usr/bin/vulcan-agent" \
    ./cmd/vulcan-agent
  CGO_ENABLED=0 GOOS=windows GOARCH=amd64 "$GO_BINARY" build \
    -trimpath -ldflags "$LDFLAGS" \
    -o "$DIST_DIR/VulcanAgent.exe" \
    ./cmd/vulcan-agent
)

chmod 0755 "$STAGING_DIR/linux-amd64/usr/bin/vulcan-agent"
install -m 0644 "$AGENT_ROOT/packaging/linux/vulcan-agent.service" "$STAGING_DIR/linux-amd64/lib/systemd/system/vulcan-agent.service"
install -m 0644 "$AGENT_ROOT/packaging/linux/vulcan-agent-user.service" "$STAGING_DIR/linux-amd64/usr/lib/systemd/user/vulcan-agent-user.service"
sed "s/@VERSION@/$VERSION/g" "$AGENT_ROOT/packaging/linux/control" > "$STAGING_DIR/linux-amd64/DEBIAN/control"
install -m 0755 "$AGENT_ROOT/packaging/linux/postinst" "$STAGING_DIR/linux-amd64/DEBIAN/postinst"
install -m 0755 "$AGENT_ROOT/packaging/linux/prerm" "$STAGING_DIR/linux-amd64/DEBIAN/prerm"
install -m 0755 "$AGENT_ROOT/packaging/linux/postrm" "$STAGING_DIR/linux-amd64/DEBIAN/postrm"

dpkg-deb --root-owner-group --build "$STAGING_DIR/linux-amd64" "$DIST_DIR/vulcan-agent_${VERSION}_amd64.deb"

WIX_SOURCE="$STAGING_DIR/VulcanAgent.rendered.wxs"
sed \
  -e "s|@VERSION@|$VERSION|g" \
  -e "s|@BINARY@|dist/VulcanAgent.exe|g" \
  "$AGENT_ROOT/packaging/windows/VulcanAgent.wxs" > "$WIX_SOURCE"

if [ -n "$WIX_CANDLE" ] && [ -n "$WIX_LIGHT" ] && [ -n "$MONO_BINARY" ]; then
  (
    cd "$AGENT_ROOT"
    "$MONO_BINARY" "$WIX_CANDLE" -nologo -arch x64 \
      -out "dist/staging/VulcanAgent.wixobj" "dist/staging/VulcanAgent.rendered.wxs"
    "$MONO_BINARY" "$WIX_LIGHT" -nologo \
      -out "dist/VulcanAgent-Windows-x64.msi" \
      "dist/staging/VulcanAgent.wixobj"
  )
else
  if [ -z "$WIXL_BINARY" ] || [ ! -x "$WIXL_BINARY" ]; then
    echo "WiX candle/light (with Mono) or wixl is required to produce the MSI." >&2
    exit 1
  fi
  if [ -z "$MSIBUILD_BINARY" ] && [ -x "$(dirname "$WIXL_BINARY")/msibuild" ]; then
    MSIBUILD_BINARY="$(dirname "$WIXL_BINARY")/msibuild"
  fi
  if [ -z "$MSIBUILD_BINARY" ] || [ ! -x "$MSIBUILD_BINARY" ]; then
    echo "msibuild is required with wixl to enforce hidden and secure MSI properties." >&2
    exit 1
  fi
  WIXL_SOURCE="$STAGING_DIR/VulcanAgent.wixl.wxs"
  sed \
    -e 's/ Secure="yes"//g' \
    -e 's/ Hidden="yes"//g' \
    "$WIX_SOURCE" > "$WIXL_SOURCE"
  WIXL_ARGUMENTS=(-a x64 -o "$DIST_DIR/VulcanAgent-Windows-x64.msi")
  if [ -n "$WIXL_WXIDIR" ]; then
    WIXL_ARGUMENTS+=(--wxidir "$WIXL_WXIDIR")
  fi
  (
    cd "$AGENT_ROOT"
    "$WIXL_BINARY" "${WIXL_ARGUMENTS[@]}" "$WIXL_SOURCE"
    "$MSIBUILD_BINARY" "$DIST_DIR/VulcanAgent-Windows-x64.msi" -q \
      "UPDATE Property SET Value = 'WIX_DOWNGRADE_DETECTED;WIX_UPGRADE_DETECTED;VULCAN_SERVER;ENROLLMENT_TOKEN;AGENT_PROFILE;SITE' WHERE Property = 'SecureCustomProperties'
       INSERT INTO Property (Property, Value) VALUES ('MsiHiddenProperties', 'VULCAN_SERVER;ENROLLMENT_TOKEN')
       UPDATE CustomAction SET Type = 10291 WHERE Action = 'SetEnrollAgentData'
       UPDATE CustomAction SET Type = 11282 WHERE Action = 'EnrollAgent'"
  )
fi

(
  cd "$AGENT_ROOT"
  "$GO_BINARY" run ./cmd/vulcan-agent-sbom \
    --binary "$STAGING_DIR/linux-amd64/usr/bin/vulcan-agent" \
    --version "$VERSION" \
    --output "$DIST_DIR/vulcan-agent_${VERSION}_sbom.cdx.json"
)

sha256sum \
  "$DIST_DIR/VulcanAgent.exe" \
  "$DIST_DIR/VulcanAgent-Windows-x64.msi" \
  "$DIST_DIR/vulcan-agent_${VERSION}_amd64.deb" \
  "$DIST_DIR/vulcan-agent_${VERSION}_sbom.cdx.json" \
  > "$DIST_DIR/SHA256SUMS"

mkdir -p "$REPOSITORY_ROOT/frontend/web/public/agent-v2"
install -m 0644 "$DIST_DIR/VulcanAgent-Windows-x64.msi" "$REPOSITORY_ROOT/frontend/web/public/agent-v2/VulcanAgent-Windows-x64.msi"
install -m 0644 "$DIST_DIR/VulcanAgent.exe" "$REPOSITORY_ROOT/frontend/web/public/agent-v2/VulcanAgent.exe"
install -m 0644 "$DIST_DIR/vulcan-agent_${VERSION}_amd64.deb" "$REPOSITORY_ROOT/frontend/web/public/agent-v2/vulcan-agent_amd64.deb"
install -m 0644 "$DIST_DIR/vulcan-agent_${VERSION}_sbom.cdx.json" "$REPOSITORY_ROOT/frontend/web/public/agent-v2/vulcan-agent_sbom.cdx.json"
install -m 0644 "$DIST_DIR/SHA256SUMS" "$REPOSITORY_ROOT/frontend/web/public/agent-v2/SHA256SUMS"

echo "Vulcan Agent release $VERSION built in $DIST_DIR"
