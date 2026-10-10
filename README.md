# MateBook E 2023 DSI driver — Linux 6.12 backport

Experimental port of hockinglee's `matebook-e-dsi-dkms` for Huawei MateBook E 2023 (DRR-W56), Linux **6.12.107 / Debian 13**.

## Status: ported and built, hardware validation pending

All six driver files touched by hockinglee's 7.2.3 DSI patch have corresponding Linux 6.12 implementations; the VBT sequence handling and DSC splitter preservation have been adapted to the 6.12 APIs. Linux 6.12.107 module compilation and an isolated DKMS build using the Debian package **succeeded**. No hardware validation has been carried out: there is no guarantee of OLED, DPMS, S3 or S4 operation yet.

The package `matebook-e-dsi-dkms` installs the experimental complete i915 source tree and enables DKMS autobuild. Do not deploy without a known-good fallback kernel/boot entry and remote/external display access. Installation may replace a functioning i915 on the next boot.

## Reproduce the local build (no installation)

Obtain the pristine Linux 6.12.107 source, then:

```sh
./scripts/prepare-source.sh /path/to/linux-6.12.107 /tmp/matebook-i915-612
make -C /tmp/matebook-i915-612 KDIR=/lib/modules/6.12.107+deb13-amd64/build -j4
```

The Debian package uses standard `dh_dkms`; a full isolated DKMS build has passed on 6.12.107. On-device testing is still required.

## Kernel support

No version exclusion rule is used by DKMS. The shipped i915 tree is derived from Linux 6.12.107, and compatibility with newer 6.12 stable point releases is intended, but **only compilation against 6.12.107 has been verified so far**. A complete on-device validation is required.
