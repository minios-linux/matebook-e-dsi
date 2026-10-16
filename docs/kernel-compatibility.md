# Target-kernel DRM API compatibility

## Linux 6.12.113 restore API

The 0.0.3 package failed during DKMS compilation against Debian
`6.12.113+deb13-amd64`. Its full build log reported two API mismatches in
`display/intel_fbdev.c`:

- `drm_fb_helper_restore_fbdev_mode_unlocked()` now takes `bool force`;
- `drm_client_funcs.restore` now takes the same additional argument.

Version 0.0.4 supports both signatures. `driver/compat/configure.sh` compiles
small type checks using **the selected kernel's Kbuild**. The helper and
callback are checked independently. There is no `LINUX_VERSION_CODE`
threshold, kernel-version exclusion, incompatible-function-pointer cast or
warning suppression. An unrecognized API or broken toolchain stops with
the probe compiler logs instead of silently assuming the old signature.

For the new callback, `force` is forwarded to the new DRM helper. The old
callback uses normal, non-forced restoration; the old helper is called with
its original signature. Tests cover both API shapes, independent combinations,
missing fbdev/VMA and helper failures.

## Build integration

The wrapper Makefile runs the probes before compiling i915 and generates
`drivers/gpu/drm/i915/matebook_kernel_compat.h`. The header is not a source
file and is regenerated for every requested kernel. Its contents are only
replaced when they change, avoiding unnecessary recompilation. `make clean`
removes it.

The Debian package installs `compat/` alongside the driver Makefile in
`/usr/src/matebook-e-dsi-0.0.4`. The source preparation script copies the same
files and applies `patches/drm-fbdev-restore-compat.patch`.

Always use the wrapper, for example:

```sh
make -C driver KDIR=/usr/src/linux-headers-6.12.113+deb13-amd64 -j8
```

For a prepared source tree or DKMS source directory, use its top-level
Makefile instead of calling Kbuild directly on the i915 subdirectory.

The selected APIs were verified as old/old for 6.12.107 and 6.12.111 and
new/new for 6.12.113. Full external module builds passed for all three.
These are compilation checks; they do not establish additional OLED,
DPMS, S3 or S4 acceptance.
