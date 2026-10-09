"""Build script for the pd-cds-api-bin native runtime distribution.

A data-only wheel with an explicit PEP 425 platform tag; the payload files
are staged by scripts/stage-frontier-client.sh (or CI) before building.
"""

import os

from setuptools import setup
from setuptools.command.bdist_wheel import bdist_wheel

# Wheels carrying a compiled runtime must not be py3-none-any. The platform
# tag is supplied by the build environment (CI sets it per-arch); locally we
# derive it from the host machine, matching the manylinux_2_28 floor that
# scripts/build-frontier-client.sh builds against.
PLAT = os.environ.get("FRONTIER_WHEEL_PLAT") or f"manylinux_2_28_{os.uname().machine}"

_here = os.path.dirname(os.path.abspath(__file__))
_pkg = os.path.join(_here, "src", "pd_cds_api_bin")
_missing = [f for f in ("fn-fileget", "libpacparser.so.1", "frontier-manifest.json")
            if not os.path.isfile(os.path.join(_pkg, f))]
if _missing:
    msg = (
        f"pd-cds-api-bin: missing native runtime file(s): {', '.join(_missing)}.\n"
        "Stage them first:  scripts/stage-frontier-client.sh\n"
        "(builds via podman/docker from the pinned fermitools/frontier revision)"
    )
    raise SystemExit(msg)


class PlatformWheel(bdist_wheel):
    """Data-only wheel with an explicit PEP 425 platform tag.

    Mirrors the nvidia-*-cudnn pattern: the importable package sits at the
    wheel root, the tag is py3-none-<platform> (no interpreter/ABI coupling,
    since the payload is a standalone executable + dlopen'd library), and
    auditwheel's ELF/glibc checks still apply because the tag is non-any.
    """

    def finalize_options(self) -> None:
        """Pin the wheel tag to py3-none-<platform> after base finalization."""
        super().finalize_options()
        self.python_tag = "py3"
        self.abi_tag = "none"
        self.plat_name_supplied = True
        self.plat_name = PLAT


setup(cmdclass={"bdist_wheel": PlatformWheel})
