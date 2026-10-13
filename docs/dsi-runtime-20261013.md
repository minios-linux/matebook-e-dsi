# Residual transient bands: device evidence, 2026-10-13

The user reports occasional horizontal colored-noise bands during composited
updates in multiple desktop environments. Bands can cover the left half,
the right half or the entire width. The earlier recovery after an Xfce
composition cycle was temporary and does not establish an Xfce-only defect.

SSH access was established to the device at `10.9.0.5` as `live`.
The running kernel is `6.12.111+deb13-amd64`. The i915 module path remains
`/lib/modules/6.12.111+deb13-amd64/updates/dkms/i915.ko`; the module's warning
trace identifies the `matebook-e-dsi/0.0.2` build. The package itself is not
registered in the live dpkg database. During collection, the active session
was Xfce/X11; the supplied image shows a different desktop session.

## Register readout

Registers were read through a read-only mapping of PCI resource0. No MMIO
writes were performed. The screen entered standby during collection, so
one all-zero sample was rejected; the screen was woken with
`DISPLAY=:0 xset dpms force on` before the DSC comparison was repeated.

| Register | Value |
| --- | --- |
| Pipe A DSS_CTL1 | `0x80000500` |
| Pipe A DSS_CTL2 | `0x80008500` |
| DSI0/DSI1 TRANS_FUNC_CONF | both `0x18160300` |
| DSI0 CMD_FRMCTL | `0x20000001` |
| DSI1 CMD_FRMCTL | `0x00000001` |
| DSI0/DSI1 HTOTAL | both `0x054f04ff` |
| DSI0/DSI1 VTOTAL | both `0x0681063f` |
| UTIL_PIN_CTL | `0x80080000` |
| DSI_PIN_BUF_CTL | `0xc0000000` |

Both DSC engines are enabled, JOINER is disabled and the splitter is
enabled. Each branch has buffer target depth 1280. Both DSC engines have
identical PPS values; PPS2 is `0x05000640`, describing 1280x1600 per engine.
PPS3 is `0x05000028`, describing a 1280x40 slice.

This confirms that the logged `dsc_split=false` and picture width 1280
are incorrect software readout for this two-engine DSI configuration, not
evidence that the right DSC engine is off. The old readout requires JOINER,
whereas the AUR patch deliberately disables it for DSI.

A 500-sample read-only observation over 0.662 seconds found the
FRAME_IN_PROGRESS bit set in 399 samples on DSI0 and 398 on DSI1, with one
sample differing between the links. Neither FRAME_UPDATE_REQUEST bit was
observed set. The two reads are sequential, so the one differing sample
does not prove a real link synchronization fault. No visual correlation
with an artifact was available during this short observation.

Both DSI interrupt masks read `0xffffffff`; both interrupt identity
registers read zero. These idle snapshots and the absence of journal
timeouts do not exclude a transient transfer error.

## VBT comparison

The live `i915_vbt` blob was collected and decoded locally with
`intel_vbt_decode` from Debian intel-gpu-tools 2.0-1, unpacked outside the
system. No diagnostic package was installed on the device.

Panel 0 uses command mode, four lanes, front/back dual link without overlap,
and DSC 1.1. The INIT_OTP sequence configures both panel controllers through
vendor page D2, including fixed DSC fields and rate-control tables.

The actual registers on **each** encoder match the panel programming for:

- 14 scalar fields: picture width/height, slice width/height, initial
  transmit delay, scale increment/decrement, first-line BPG offset,
  non-first-line and slice BPG offsets, initial/final offsets, RC model
  size and RC edge factor;
- all 14 RC buffer thresholds;
- all 15 RC range tuples (minimum QP, maximum QP, six-bit BPG offset).

Not every DSC/PPS field is covered by this comparison. In particular,
the vendor sequence does not expose initial decoder delay in the compared
register range. Matching the tested fields therefore does not prove the
whole end-to-end DSC path correct.

The VBT sends `SET_TEAR_SCANLINE` (`44 04 c4`) to both links: scanline 1220.
This is a firmware-provided setting, not a proposed replacement value.
Its interaction with host frame-update scheduling needs investigation;
it must not be changed solely because artifacts occur in the lower area.

## Remaining investigation

The comparison narrows the next work to transient transfer/scanout behavior,
TE/frame scheduling and fields not covered above. No additional functional
driver change has been justified by this collection. Attempts to collect
pipe interrupt status and CDCLK were interrupted by loss of SSH access;
even a subsequent `hostname; uptime` connection timed out.

Artifacts were retained in `build/matebook-e-dsi-runtime-20261013/` as
`matebook-20261013.vbt`, `matebook-20261013-vbt.txt`,
`matebook-20261013-dsc.json` and `compare-matebook-dsc.py`.
