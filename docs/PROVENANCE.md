# Source and license

This is a modified subset of Linux USB audio. Upstream copyrights, SPDX identifiers and alternative per-file licenses are preserved. The driver is GPLv2; [NOTICE](../NOTICE) describes the license scope, including the original helper tools covered by [LICENSE-tools](../LICENSE-tools).

## Source versions

- `kernel-source/`: Ubuntu `linux-hwe-7.0 7.0.0-34.34~24.04.1`. The development records also identify the same USB-audio source contents in Ubuntu `linux 7.0.0-34.34`; their build configurations differ. [Ubuntu source catalog](https://launchpad.net/ubuntu/+source/linux)
- `kernel-source-debian-6.12/`: Debian `linux-source-6.12 6.12.107-1`. [Debian source](https://sources.debian.org/src/linux/6.12.107-1/)
- `tests/fixtures/v0.3/`: older modified Ubuntu-derived source used by regression tests; it is GPL source, not current driver code

These source identities come from the development records. `SHA256SUMS` identifies the supplied files; it is not a distributor signature.

## Local changes

The Fostex changes add explicit device opt-in, native DSD formats, mode/rate setup and checks, and defer unsolicited probe-time hardware setup. Debian also selects the mode before preparing the rate. Changed source files carry modification notices dated 2026-10-02. These changes are not attributed to upstream authors.

The two complete patches in `patches/` include these changes and notices. Their distribution baselines were reconstructed by reversing the preserved earlier project patches, without fuzz. They were not reconstructed from newly downloaded source archives. See [porting](PORTING.md).

No vendor firmware or Windows driver binaries are included.
