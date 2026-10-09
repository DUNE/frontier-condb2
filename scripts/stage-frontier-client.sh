#!/usr/bin/env bash
# Stage the native Frontier runtime into the pd-cds-api-bin package.
#
#   scripts/stage-frontier-client.sh                 # container build at pinned ref
#   scripts/stage-frontier-client.sh --from-ci RUN_ID # download CI runtime artifact
#   scripts/stage-frontier-client.sh --check          # exit 1 if not staged
#
# The pinned upstream revision is read from $FRONTIER_REF (env) or the
# ./FRONTIER_REF file at the repo root. Artifacts land in
# client/pd-cds-api-bin/src/pd_cds_api_bin/ (gitignored; CI does the same).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="$REPO_ROOT/client/pd-cds-api-bin/src/pd_cds_api_bin"
MODE="build"
CI_RUN=""
ARCH=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --from-ci) MODE="ci"; CI_RUN="$2"; shift 2 ;;
        --check) MODE="check"; shift ;;
        --arch) ARCH="$2"; shift 2 ;;
        *) echo "Unknown option: $1" >&2; exit 2 ;;
    esac
done

check_staged() {
    [[ -x "$DEST/fn-fileget" && -f "$DEST/libpacparser.so.1" \
        && -f "$DEST/.frontier-manifest.json" ]]
}

if [[ "$MODE" == "check" ]]; then
    if check_staged; then
        echo "Native runtime staged: $DEST"
    else
        cat >&2 <<EOF
Native Frontier runtime is missing from: $DEST

Run one of:
  scripts/stage-frontier-client.sh            # builds via podman/docker (manylinux)
  scripts/stage-frontier-client.sh --from-ci <run-id>

Requires podman or docker (build mode), or gh (CI mode).
EOF
        exit 1
    fi
    exit 0
fi

if [[ "$MODE" == "ci" ]]; then
    command -v gh >/dev/null || { echo "gh CLI required for --from-ci" >&2; exit 1; }
    [[ -n "$ARCH" ]] || ARCH="$(uname -m)"
    artifact="frontier-runtime_${ARCH}"
    tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
    gh run download "$CI_RUN" -R "$(git -C "$REPO_ROOT" remote get-url --push origin)" \
        -n "$artifact" -D "$tmp"
    cp "$tmp/fn-fileget" "$tmp/libpacparser.so.1" "$tmp/.frontier-manifest.json" "$DEST/"
else
    ref="${FRONTIER_REF:-$(cat "$REPO_ROOT/FRONTIER_REF" 2>/dev/null || true)}"
    [[ -n "$ref" ]] || { echo "Set FRONTIER_REF (env or ./FRONTIER_REF file)" >&2; exit 1; }
    tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
    args=(--ref "$ref" --out "$tmp")
    [[ -n "$ARCH" ]] && args+=(--arch "$ARCH")
    "$REPO_ROOT/scripts/build-frontier-client.sh" "${args[@]}"
    mkdir -p "$DEST"
    cp "$tmp/fn-fileget" "$tmp/libpacparser.so.1" "$tmp/.frontier-manifest.json" "$DEST/"
fi

chmod 755 "$DEST/fn-fileget"
"$REPO_ROOT/scripts/stage-frontier-client.sh" --check
