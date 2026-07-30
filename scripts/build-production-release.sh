#!/usr/bin/env bash

set -euo pipefail
umask 022

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="${1:-0.3.0}"
COMMIT_SHA="$(git -C "$ROOT_DIR" rev-parse HEAD)"
BUILD_ID="$(date -u +%Y%m%dT%H%M%SZ)"
DIST_DIR="$ROOT_DIR/dist"
RELEASE_NAME="vulcan-${VERSION}-linux-amd64"
RELEASE_DIR="$DIST_DIR/$RELEASE_NAME"

if ! command -v syft >/dev/null 2>&1; then
  echo "syft é obrigatório para gerar o SBOM CycloneDX da release." >&2
  exit 1
fi

mkdir -p "$DIST_DIR"
if [[ -e "$RELEASE_DIR" ]]; then
  echo "A release já existe e não será sobrescrita: $RELEASE_DIR" >&2
  exit 1
fi

mkdir -p \
  "$RELEASE_DIR/agents" \
  "$RELEASE_DIR/images" \
  "$RELEASE_DIR/manifests/sbom" \
  "$RELEASE_DIR/migrations" \
  "$RELEASE_DIR/secrets"

docker build \
  --target runtime \
  --label "org.opencontainers.image.version=$VERSION" \
  --label "org.opencontainers.image.revision=$COMMIT_SHA" \
  --label "org.opencontainers.image.created=$BUILD_ID" \
  -t "vulcan/backend:$VERSION" \
  -f "$ROOT_DIR/backend/api/Dockerfile" "$ROOT_DIR"

docker build \
  --target migration \
  --label "org.opencontainers.image.version=$VERSION" \
  --label "org.opencontainers.image.revision=$COMMIT_SHA" \
  --label "org.opencontainers.image.created=$BUILD_ID" \
  -t "vulcan/backend-migration:$VERSION" \
  -f "$ROOT_DIR/backend/api/Dockerfile" "$ROOT_DIR"

docker build \
  --build-arg NEXT_PUBLIC_API_URL=/api \
  --build-arg NEXT_PUBLIC_ENVIRONMENT=production \
  --build-arg NEXT_PUBLIC_LOCAL_TEST_AUTH=false \
  --build-arg NEXT_PUBLIC_MOCK_AUTH=false \
  --label "org.opencontainers.image.version=$VERSION" \
  --label "org.opencontainers.image.revision=$COMMIT_SHA" \
  --label "org.opencontainers.image.created=$BUILD_ID" \
  -t "vulcan/frontend:$VERSION" \
  -f "$ROOT_DIR/frontend/web/Dockerfile" "$ROOT_DIR"

docker build \
  --target runtime \
  --label "org.opencontainers.image.version=$VERSION" \
  --label "org.opencontainers.image.revision=$COMMIT_SHA" \
  --label "org.opencontainers.image.created=$BUILD_ID" \
  -t "vulcan/discovery:$VERSION" \
  -f "$ROOT_DIR/backend/discovery/Dockerfile" "$ROOT_DIR"

runtime_images=(
  "vulcan/backend:$VERSION"
  "vulcan/backend-migration:$VERSION"
  "vulcan/frontend:$VERSION"
  "vulcan/discovery:$VERSION"
  "postgres:16-alpine"
  "postgres:15-alpine"
  "redis:7.4-alpine"
  "nginx:1.27-alpine"
  "alpine:3.22"
  "evoapicloud/evolution-api:v2.3.7"
)

for image in "${runtime_images[@]}"; do
  docker image inspect "$image" >/dev/null
done

docker image save "${runtime_images[@]}" | gzip -9 > "$RELEASE_DIR/images/vulcan-images.tar.gz"

for image in "vulcan/backend:$VERSION" "vulcan/backend-migration:$VERSION" "vulcan/frontend:$VERSION" "vulcan/discovery:$VERSION"; do
  sbom_name="$(tr '/:' '__' <<<"$image").cdx.json"
  syft "$image" -o cyclonedx-json="$RELEASE_DIR/manifests/sbom/$sbom_name" >/dev/null
done

cp "$ROOT_DIR/deploy/production/compose.yml" "$RELEASE_DIR/compose.yml"
cp "$ROOT_DIR/deploy/production/nginx.conf" "$RELEASE_DIR/nginx.conf"
cp "$ROOT_DIR/deploy/production/.env.production.example" "$RELEASE_DIR/.env.production.example"
cp "$ROOT_DIR/deploy/production/"*.sh "$RELEASE_DIR/"
cp "$ROOT_DIR/database/supabase/migrations/"*.sql "$RELEASE_DIR/migrations/"
cp "$ROOT_DIR/deploy/production/secrets/.gitignore" "$RELEASE_DIR/secrets/.gitignore"

if compgen -G "$ROOT_DIR/frontend/web/public/agent-v2/*" >/dev/null; then
  cp "$ROOT_DIR/frontend/web/public/agent-v2/"* "$RELEASE_DIR/agents/"
  (
    cd "$RELEASE_DIR/agents"
    find . -maxdepth 1 -type f ! -name SHA256SUMS -printf '%f\0' \
      | sort -z \
      | xargs -0 sha256sum > SHA256SUMS
  )
fi

cat > "$RELEASE_DIR/manifests/release.json" <<EOF
{
  "product": "Vulcan",
  "version": "$VERSION",
  "commit": "$COMMIT_SHA",
  "build": "$BUILD_ID",
  "platform": "linux/amd64",
  "imagesArchive": "images/vulcan-images.tar.gz",
  "sourceIncluded": false
}
EOF

docker image inspect "${runtime_images[@]}" > "$RELEASE_DIR/manifests/images.json"
find "$RELEASE_DIR" -type f -exec chmod 0644 {} +
find "$RELEASE_DIR" -type f -name '*.sh' -exec chmod 0755 {} +
(cd "$RELEASE_DIR" && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS)

tar -C "$DIST_DIR" -czf "$DIST_DIR/$RELEASE_NAME.tar.gz" "$RELEASE_NAME"
(cd "$DIST_DIR" && sha256sum "$RELEASE_NAME.tar.gz" > "$RELEASE_NAME.tar.gz.sha256")

echo "Release criada: $DIST_DIR/$RELEASE_NAME.tar.gz"
echo "Versão: $VERSION"
echo "Commit: $COMMIT_SHA"
echo "Build: $BUILD_ID"
