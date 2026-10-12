# Linux 6.12 backport verification

The backport adapts hockinglee's Linux 7.2.3 DSI patch to Linux 6.12.107.
It updates all six affected display driver files, including VBT sequence
handling and DSC splitter preservation.

The source patch applies to pristine Linux 6.12.107 with `--fuzz=0`.
The resulting i915 module compiles against
`linux-headers-6.12.107+deb13-amd64`. An isolated DKMS build using the Debian
package also succeeded. DKMS automatic builds are enabled without a
kernel-version exclusion.

The 0.0.1 package also built and installed through DKMS for 6.12.111 in the
MiniOS image build. The user reports a working image with horizontal colored
noise on the physical MateBook. Compilation alone does not validate OLED,
DPMS or suspend operation.
The isolated DKMS build could not sign the module because the host's MOK
private key was inaccessible; Secure Boot deployment requires signing.

## Colored-noise investigation, 2026-10-11

The current AUR repository is at commit `41ef40f`. Its patch is byte-identical
to `patches/upstream-7.2.3.patch`. The main DSI additions and splitter masks
are present in the 6.12 port, with API and formatting adaptations.

However, porting that patch alone omits a fix already in its base kernel:
Linux commit [`c63d00e388f2`](https://github.com/torvalds/linux/commit/c63d00e388f2240c732bf1c89dc48bc8ff98089d),
"drm/i915/vdsc: Use the DSC config tables for DSI panels". It selects the
predefined RC tables instead of interpolating RC parameters for DSI DSC 1.1
panels. Upstream explains that some panels have hardcoded PPS parameters and
that differing interpolated parameters cause display noise.

Read-only SSH diagnostics on `matebook-e-64` confirmed:

- Linux `6.12.111+deb13-amd64`, Alder Lake-UP4 GPU `8086:46aa`, BIOS 1.29;
- replacement i915 at `/lib/modules/6.12.111+deb13-amd64/updates/dkms/i915.ko`;
- no `nomodeset` in the boot command line;
- DSI DSC 1.1, 8 bpc, 8 compressed bpp, 2560x1600, two 1280x40 slices;
- the old source takes `calculate_rc_params()` on this display version;
- kernel state verification reports picture width 2560 vs 1280 and split
  enabled vs disabled, alongside timing differences.

Version 0.0.2 backports the RC table condition, in both the shipped source and
`patches/dsi-dsc-1.1-rc-params.patch`. `prepare-source.sh` applies it after
the initial backport. Other output types and DSC versions retain their
existing RC selection. Full external-module development builds passed in
the persistent Trixie amd64 container for 6.12.107 and 6.12.111.

The split/width warning is a separate readout issue: 6.12 infers two DSC
engines from `RIGHT_BRANCH_VDSC_ENABLE && JOINER_ENABLE`, whereas the AUR
fix deliberately clears JOINER for DSI. It does not by itself prove that
only one engine was programmed. Keep this warning visible while validating
the RC correction; it has not been suppressed.

### Device acceptance for the RC correction

Install the newly versioned package with matching kernel headers and check
that DKMS completes. Rebuild the boot initramfs through the system's normal
boot-image mechanism before rebooting, so an old early-loaded i915 does not
mask the result. For MiniOS live images, include the new module in a rebuilt
kernel layer/boot image. Keep the previous boot image as a fallback.

After a cold boot, inspect the OLED with static and moving content. Compare
the DSC debug state with the old values: for this panel the table branch
changes `first_line_bpg_offset` from 14 to 12 and `initial_dec_delay` from
1004 to 897. The dumped `rc_edge_factor` and `rc_tgt_offset` fields remain
zero in this implementation; they are not a reliable branch-selection check.
Record a photo and the kernel journal. Then test DPMS separately, followed
by S3 and S4. None of these acceptance results is claimed by the source or
build verification above.

## Device follow-up: residual update artifacts

The user tested the correction and reported a large reduction in noise,
with residual transient bands during redraw. They disappear when the image
stops changing and occur mainly in the lower portion of the screen.
SSH diagnostics confirmed the table-derived RC values above, hardware
acceleration with Mesa Intel Iris Xe, and the native 2560x1600 mode.

A runtime FBC comparison set
`/sys/kernel/debug/dri/0/i915_params/enable_fbc` from 1 to 0. The user
reported that bands persisted. The parameter was restored to 1.

Next, Xfce composition was temporarily disabled through
`xfconf-query -c xfwm4 -p /general/use_compositing -s false`.
The user subsequently re-enabled composition and reported no bands.
Readback confirmed composition enabled, `vblank_mode=auto`, FBC enabled
and compressing, and unchanged software DSC/mode configuration. The primary
framebuffer ID changed from 269 in the earlier capture to 272 in the clean
capture, with the same format, modifier and dimensions.

This is an observed recovery after a composition cycle, not proof that
composition itself is faulty or that the driver is fully fixed. Buffer
replacement and redraw synchronization remain hypotheses. Reproduction
after a cold boot and DPMS is needed to determine whether the residual
problem returns. No permanent compositor workaround has been added.

## Physical panel size: Xorg loses the KMS dimensions

On `matebook-e-64`, a direct `DRM_IOCTL_MODE_GETCONNECTOR` query for
connector 241 returns `mm_width=271`, `mm_height=170`. The i915 debugfs
connector dump agrees. The DSI EDID blob is empty, while Xrandr reports
`0mm x 0mm`. Thus i915 exports the physical size correctly through the DRM
userspace ABI; it is not a missing panel-size fix in the kernel backport.

The running X server is `2:21.1.16-1.3+deb13u4`, using the modesetting DDX.
In the corresponding Xorg 21.1.16 source, `drmmode_output_init()` copies the
KMS dimensions into `output->mm_width/mm_height`. Later,
`drmmode_output_get_modes()` calls `xf86OutputSetEDID(output, NULL)` for
this EDID-less panel. That function clears both dimensions, and the
modesetting DDX does not restore the KMS values after the call.

The user requested that Xorg remain unchanged. A driver-side compatibility
solution would expose a synthetic EDID derived from the VBT fixed mode and
its physical dimensions. Existing connector dimensions alone cannot fix
the Xorg reset described above. No synthetic EDID has been implemented yet.
