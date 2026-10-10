# Linux 6.12 backport verification

The backport adapts hockinglee's Linux 7.2.3 DSI patch to Linux 6.12.107.
It updates all six affected display driver files, including VBT sequence
handling and DSC splitter preservation.

The source patch applies to pristine Linux 6.12.107 with `--fuzz=0`.
The resulting i915 module compiles against
`linux-headers-6.12.107+deb13-amd64`. An isolated DKMS build using the Debian
package also succeeded. DKMS automatic builds are enabled without a
kernel-version exclusion.

Hardware behavior and newer Linux 6.12 revisions have not been tested.
Compilation alone does not validate OLED, DPMS or suspend operation.
The isolated DKMS build could not sign the module because the host's MOK
private key was inaccessible; Secure Boot deployment requires signing.
