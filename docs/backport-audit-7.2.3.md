# Backport audit against Linux 7.2.3 + the AUR patch

## Reference and provenance

This audit uses the exact Linux **7.2.3** archive specified by AUR commit
`41ef40f`, not the 7.2 release tag or the current kernel branch.
Archive SHA256:
`8ba259e8e7b13ec6ef0941c8a39ad90b24bd4a4d6c0010ba6bafb794550ecd03`.
The AUR patch SHA256 is
`882842e895d3c8f746d58e895a406519c666a06612d425b3f38cf4ca907e0b04`.
Both match the PKGBUILD. The patch applies without fuzz.

The pristine 6.12.107 archive SHA256 is
`a5f8c5be3fde2d6d9ca14e9631642cf1f44487143f11059da730dcd5892e307a`.
Preparing it with the repository scripts reproduces the shipped driver
files, excluding the kernel's untracked `.gitignore`. The audit artifacts
and per-file diffs are in `build/matebook-e-dsi-audit-20261013/`.

## Original AUR changes

The six-file AUR patch was compared with the port, including call placement,
register masks, operation order and the VBT v3 reset/rest split.

| Group | Result |
| --- | --- |
| Firmware HSYNC/VSYNC/VTOTAL capture and restore | Present; same validity test and master-port selection |
| Periodic command frame update detection/restore | Present; correct CMD_FRMCTL register |
| First-frame request before vblank enable | Present; same request, polling and enable order |
| Second TE pin-buffer restore and shared UTIL_PIN PWM guard | Present; same conditions and register value preservation |
| Leading DELAY/GPIO reset block before transcoder setup | Present; v3-size checks and old-sequence fallback retained |
| DSC JOINER exclusion and splitter state preservation | Present; 6.12 VDSC-enable names mapped to the same bits |

The 7.2 `intel_panel_prepare/unprepare()` additions notify drm_panel
followers through dummy panel functions. They do not replace the VBT panel
power/reset commands. Their absence in 6.12 is not an omitted OLED reset.

## Missing base-kernel dependencies corrected in 0.0.3

Copying the AUR patch alone had left additional DSI changes from its base
kernel behind. These are separate from the previously ported DSC RC table
selection (`c63d00e388f2`).

- **`1ca3991f6400`: let HW maintain HS-TRAIL timing.** The old driver forced
  clock/data TRAIL values in escape-clock units. Upstream explains that
  rounding TRAIL together with EXIT can exceed the MIPI TEOT limit. Both
  TRAIL overrides are removed, matching the reference. This affects the
  actual MateBook configuration.
- **`ca677505e477`: separate clock and data lane prepare timing.** PREPARE
  and ZERO are calculated separately for the clock and data lanes, instead
  of using the larger PREPARE for both. The complete PHY calculation now
  matches the reference. On this MateBook both PREPARE inputs are 50 ns,
  so this part does not independently change its PREPARE result.
- **`1c57014325ef`: enforce pipeline flush for HS commands.** The header
  explicitly clears stale LP/flush/fence bits and sets PIPELINE_FLUSH for
  HS transmission. The inspected MateBook VBT sends LP commands, so this
  is not evidence that HS command arbitration caused the observed bands.
- **`765a2635cd25` and `e8a7efa81d73`: honor VBT blanking/LP clock flags.**
  Packed flag positions are added without changing the 122-byte VBT config
  layout. Both options are zero in this panel's BDB 248 config. The driver
  now explicitly clears unused bits as the reference does.

These changes are reproduced by `patches/dsi-7.2-base-fixes.patch` after the
initial port and the DSC RC patch. They introduce no kernel-version gate.

## Device evidence and register expectations

Read-only observation on the old module found both links programmed with:

- DPHY clock timing: `0xc8690082`;
- DPHY data timing: `0x84838283`.

The corrected/reference functions produce `0xc8690000` and `0x84830083`
for the MateBook VBT inputs. The difference removes the clock/data TRAIL
override and value bits. This is a concrete active register difference,
not a conclusion that the transient artifacts are already fixed.

DSC parameters and both engines were checked separately against panel
programming in the VBT; see `dsi-runtime-20261013.md`.

## Other compared paths and remaining differences

- The TE interrupt handler, dual-link master selection and TE-enable port
  selection have the same control flow. Private/display access wrappers
  differ with kernel API refactoring.
- `icl_dsi_frame_update()` and the MMIO `intel_pipe_update_end()` path retain
  the same request ordering. Non-VRR vblank evasion and scanline offset are
  equivalent for display version 13; newer VRR and PREEMPT_RT changes were
  not transplanted into this non-VRR path.
- DRM DSC RC computation/PPS packing helpers differ only by an export
  include between these archives. DSC stream-count representation changed
  in i915, but the target two-engine/two-slice configuration produces the
  same per-engine dimensions and PPS programming.
- The original AUR-patched 7.2.3 readout **also** requires JOINER to count a
  second DSC stream. Thus the bad split/width warning is shared by that
  reference, not a uniquely incorrect adaptation to 6.12.
- New DSC slice-overhead accounting raises the target minimum DSC CDCLK
  from 198775 to 200146 kHz for these timings. The device was measured at
  307200 kHz, above both. This does not prove that every load-dependent
  bandwidth/clock decision is equivalent.
- 7.2 has wider DSB plane-commit and prefill/watermark rework. Its automatic
  DSB path can bypass the MMIO pipe-update end hook. 6.12 retains its own
  atomic/DSB architecture. These broader differences remain a boundary of
  equivalence; no speculative frame-request suppression or bulk atomic
  framework transplant was made.
- New VBT packet return-value logging, polling-helper conversions and DRM
  object/ref-tracker refactoring were reviewed as additional differences.
  A successful module build does not prove their complete runtime equality.

## Verification and hardware boundary

Eight tests compile and call the actual PHY/header functions with MMIO
stubs, and validate VBT binary layout. With `MATEBOOK_REFERENCE_TREE` set,
their outputs are also compared with the actual AUR-patched 7.2.3 functions.
The tests cover the real VBT values, differing PREPARE timings, clamping,
TRAIL override removal, LP/HS header reuse and credit exhaustion.

External-module builds passed as the unprivileged builder in the persistent
Trixie container for 6.12.107 and 6.12.111. These are build and focused
behavioral checks, not a physical signal or compositor test.
The new candidate must be cold-booted on the MateBook and exercised with
the workloads showing bands, then checked through DPMS, S3 and S4.
The reference 7.2.3 driver has not been booted on this device during the
audit, so it is not an experimentally proven artifact-free control.
