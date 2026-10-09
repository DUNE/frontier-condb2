#!/usr/bin/env bash
# Build a self-contained fn-fileget from the upstream fermitools/frontier client.
#
# Two modes:
#   scripts/build-frontier-client.sh --ref <git-ref> [--arch <x86_64|aarch64>] --out <dir>
#       Runs the build inside a quay.io/pypa/manylinux_2_28_<arch> container
#       (podman or docker) and writes artifacts to <dir> on the host.
#   scripts/build-frontier-client.sh --ref <git-ref> --out <dir> --in-container
#       Executes the raw build steps; intended to run INSIDE the manylinux
#       container. Used by --container mode and by CI (frontier-build.yml).
#
# Artifacts written to --out:
#   fn-fileget              statically linked (no libfrontier_client.so),
#                           RPATH $ORIGIN so libpacparser.so.1 resolves co-located
#   libpacparser.so.1       pacparser shared library used via dlopen
#   COPYING                 upstream license
#   Fermilab-2009.txt       upstream attribution
#   frontier-manifest.json provenance (ref, sha, version, arch, glibc floor)
set -euo pipefail

FRONTIER_REPO="https://github.com/fermitools/frontier"
PACPARSER_REPO="https://github.com/manugarg/pacparser"
PACPARSER_REF="v1.4.2"
OPENSSL_VERSION="3.0.15"
OPENSSL_URL="https://github.com/openssl/openssl/releases/download/openssl-${OPENSSL_VERSION}/openssl-${OPENSSL_VERSION}.tar.gz"
OPENSSL_PREFIX="/usr/local/openssl-static"
GLIBC_FLOOR="2.28"

REF=""
ARCH=""
OUT=""
IN_CONTAINER=0

usage() {
    echo "Usage: $0 --ref <frontier-git-ref> [--arch <x86_64|aarch64>] --out <dir> [--in-container]" >&2
    exit 2
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --ref) REF="$2"; shift 2 ;;
        --arch) ARCH="$2"; shift 2 ;;
        --out) OUT="$2"; shift 2 ;;
        --in-container) IN_CONTAINER=1; shift ;;
        *) usage ;;
    esac
done

[[ -n "$REF" && -n "$OUT" ]] || usage

build_in_container() {
    # work is deliberately NOT local: the EXIT trap runs after the function
    # scope ends; a local would be unbound there under set -u.
    work="$(mktemp -d)"
    trap 'rm -rf "$work"' EXIT

    # gcc-toolset-11 matches the gcc-11 family the client is production-built
    # with; pacparser's bundled SpiderMonkey does not build on gcc-14 (the
    # manylinux image default).
    echo "==> Installing gcc-toolset-11 + frontier build dependencies"
    dnf -q install -y gcc-toolset-11-gcc gcc-toolset-11-gcc-c++ \
        openssl-devel zlib-devel expat-devel \
        perl-core perl-IPC-Cmd perl-Data-Dumper >/dev/null
    # shellcheck disable=SC1091
    set +u  # scl_source uses unset helper vars internally
    source scl_source enable gcc-toolset-11
    set -u
    echo "    using $(gcc --version | head -1)"

    echo "==> Checking out frontier @ ${REF} (client/ only)"
    git init -q "$work/frontier"
    git -C "$work/frontier" remote add origin "$FRONTIER_REPO"
    git -C "$work/frontier" fetch --depth 1 origin "$REF"
    git -C "$work/frontier" checkout -q FETCH_HEAD
    SHA="$(git -C "$work/frontier" rev-parse FETCH_HEAD)"
    # Deterministic build timestamps: OpenSSL 3 honors SOURCE_DATE_EPOCH, and
    # the manifest's built_at records the pinned commit's date, so rebuilds of
    # the same SHA yield identical provenance (ELF bytes may still differ in
    # debug path records).
    BUILD_EPOCH="$(git -C "$work/frontier" show -s --format=%ct "$SHA")"
    export SOURCE_DATE_EPOCH="$BUILD_EPOCH"

    echo "==> Building static OpenSSL ${OPENSSL_VERSION} (no system soname deps)"
    curl -fsSL "$OPENSSL_URL" -o "$work/openssl.tar.gz"
    tar -xzf "$work/openssl.tar.gz" -C "$work"
    (
        cd "$work/openssl-${OPENSSL_VERSION}"
        ./config --prefix="$OPENSSL_PREFIX" --libdir=lib no-shared no-tests >/dev/null
        make -j"$(nproc)" >/dev/null
        make install_sw >/dev/null
    )

    echo "==> Checking out pacparser @ ${PACPARSER_REF}"
    git clone -q --depth 1 --branch "$PACPARSER_REF" "$PACPARSER_REPO" "$work/pacparser"

    echo "==> Building pacparser"
    # Sequential: bundled SpiderMonkey has parallel-build races (Text file busy)
    make -C "$work/pacparser/src" >/dev/null
    make -C "$work/pacparser/src" install
    ldconfig

    echo "==> Building frontier client objects (upstream Makefile, unmodified)"
    mkdir -p "$work/build"
    cp -r "$work/frontier/client/." "$work/build/"
    # Sequential: libfrontier_client.so depends on http/.libs created by the
    # htclient sub-make; -j races it (mirrors upstream CI usage of plain make).
    # OPENSSL_DIR redirects the build at our static OpenSSL (headers + libs).
    # Build only needed targets: upstream's `all` also links fn-req/fn-req.static,
    # whose LIBS lack -lpthread and thus fail against static OpenSSL.
    make -C "$work/build" OPENSSL_DIR="$OPENSSL_PREFIX" \
        htclient libfrontier_client.so fn-fileget.o

    echo "==> Linking self-contained fn-fileget (static frontier objects + OpenSSL, RPATH \$ORIGIN)"
    # zlib/expat stay dynamic: stable sonames (libz.so.1/libexpat.so.1) present
    # on every target distro. OpenSSL must be static: its soname differs
    # across el8 (libssl.so.10) and el9 (libssl.so.3).
    c++ -O2 -Wall -DFRONTIER_DEBUG -static-libstdc++ -static-libgcc \
        -o "$work/fn-fileget" \
        "$work/build/fn-fileget.o" "$work/build"/.libs/*.o \
        -I"$work/build/include" -I"$work/build" \
        -L"$OPENSSL_PREFIX/lib" -lssl -lcrypto \
        -lz -lexpat -ldl -lrt -lpthread -lm \
        -Wl,-rpath,'$ORIGIN'

    echo "==> Verifying ldd (no libfrontier_client.so/libstdc++, no dynamic OpenSSL)"
    local ldd_out
    ldd_out="$(ldd "$work/fn-fileget")"
    if grep -qE "libfrontier_client|libssl\.so|libcrypto\.so|libstdc\+\+" <<<"$ldd_out"; then
        echo "ERROR: binary still depends on:" >&2
        grep -E "libfrontier_client|libssl\.so|libcrypto\.so|libstdc\+\+" <<<"$ldd_out" >&2
        exit 1
    fi

    local version
    version="$(
        maj="$(sed -n 's/^FN_VER_MAJOR[ \t]*=[ \t]*//p' "$work/build/Makefile" | head -1)"
        min="$(sed -n 's/^FN_VER_MINOR[ \t]*=[ \t]*//p' "$work/build/Makefile" | head -1)"
        printf '%s.%s' "$maj" "$min"
    )"

    echo "==> Staging artifacts to ${OUT}"
    mkdir -p "$OUT"
    cp "$work/fn-fileget" "$OUT/fn-fileget"
    chmod 755 "$OUT/fn-fileget"
    local pplib
    pplib="$(ldconfig -p 2>/dev/null | sed -n '/libpacparser\.so\.1 /{s/.*=> //;p;}' | sed -n 1p)"
    if [[ -z "$pplib" || ! -e "$pplib" ]]; then
        pplib="$(ls /usr/local/lib/libpacparser.so.1* /usr/local/lib64/libpacparser.so.1* 2>/dev/null | head -1 || true)"
    fi
    [[ -n "$pplib" && -e "$pplib" ]] || { echo "ERROR: libpacparser.so.1 not found after install" >&2; exit 1; }
    cp -L "$pplib" "$OUT/libpacparser.so.1"
    cp "$work/build/COPYING" "$OUT/COPYING"
    cp "$work/build/Fermilab-2009.txt" "$OUT/Fermilab-2009.txt"

    local arch libc
    arch="$(uname -m)"
    libc="$(getconf GNU_LIBC_VERSION | sed -n 's/^glibc *//p')"

    printf '{\n  "upstream": "%s",\n  "ref": "%s",\n  "sha": "%s",\n  "frontier_version": "%s",\n  "pacparser_ref": "%s",\n  "arch": "%s",\n  "glibc_floor": "%s",\n  "glibc_build": "%s",\n  "built_at": "%s"\n}\n' \
        "$FRONTIER_REPO" "$REF" "$SHA" "$version" "$PACPARSER_REF" "$arch" "$GLIBC_FLOOR" "$libc" \
        "$(date -u -d "@${BUILD_EPOCH:-$(date +%s)}" +%Y-%m-%dT%H:%M:%SZ)" \
        > "$OUT/frontier-manifest.json"

    echo "==> Done: frontier ${version} (${SHA:0:12}) for ${arch}"
}

build_host_container() {
    local runtime image
    [[ -z "$ARCH" ]] && ARCH="$(uname -m)"
    case "$ARCH" in
        x86_64|aarch64) ;;
        *) echo "Unsupported arch: $ARCH (x86_64|aarch64)" >&2; exit 2 ;;
    esac
    runtime="$(command -v podman || command -v docker || { echo "need podman or docker" >&2; exit 1; })"
    image="quay.io/pypa/manylinux_2_28_${ARCH}"

    mkdir -p "$OUT"
    "$runtime" run --rm --platform "linux/${ARCH}" \
        -v "$PWD/scripts:/mnt/scripts:ro" \
        -v "$(cd "$OUT" && pwd)":/mnt/out \
        "$image" \
        bash /mnt/scripts/build-frontier-client.sh --ref "$REF" --out /mnt/out --in-container
}

if [[ "$IN_CONTAINER" -eq 1 ]]; then
    build_in_container
else
    build_host_container
fi
