# MateBook E 2023 DSI driver — Linux 6.12 backport

Experimental port of hockinglee's `matebook-e-dsi-dkms` for Huawei MateBook E 2023 (DRR-W56), Linux **6.12.107 / Debian 13**.

## Status: image works with noise; DSC correction awaiting device validation

All six driver files touched by hockinglee's 7.2.3 DSI patch have corresponding Linux 6.12 implementations; the VBT sequence handling and DSC splitter preservation have been adapted to the 6.12 APIs. The user reports a working OLED image with horizontal colored-noise bands on Linux 6.12.111. DPMS, S3 and S4 acceptance is still pending.

Version 0.0.2 adds a missing base-kernel dependency of the AUR patch: upstream DSC 1.1 DSI RC table selection. The corrected module builds against 6.12.107 and 6.12.111, but removal of the noise has not yet been checked on the device. See [the audit](docs/patch-compatibility.md).

The package `matebook-e-dsi-dkms` installs the experimental complete i915 source tree and enables DKMS autobuild. Do not deploy without a known-good fallback kernel/boot entry and remote/external display access. Installation may replace a functioning i915 on the next boot.

## Reproduce the local build (no installation)

Obtain the pristine Linux 6.12.107 source, then:

```sh
./scripts/prepare-source.sh /path/to/linux-6.12.107 /tmp/matebook-i915-612
make -C /tmp/matebook-i915-612 KDIR=/lib/modules/6.12.107+deb13-amd64/build -j4
```

The Debian package uses standard `dh_dkms`; a full isolated DKMS build has passed on 6.12.107. On-device testing is still required.

## Kernel support

No version exclusion rule is used by DKMS. The shipped i915 tree is derived from Linux 6.12.107. Compilation of the corrected source has been verified against 6.12.107 and 6.12.111; compatibility with later 6.12 releases still requires testing.
