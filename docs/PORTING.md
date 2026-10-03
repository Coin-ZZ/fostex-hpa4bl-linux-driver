# Porting

Use the destination kernel's USB-audio stack and port the Fostex changes into it. Copying this entire stack into an arbitrary kernel is not supported.

The complete patches are:

- `patches/full-ubuntu-7.0.0-34-fostex-native-dsd.patch`
- `patches/full-debian-6.12.107-fostex-native-dsd.patch`

The included trees already have them applied. [Source versions](PROVENANCE.md) describes their baselines.

## Changed files

- `quirks.c` / `quirks.h`: exact USB ID, default-off `fostex_dsd` option, DSD formats and mode selection
- `clock.c` / `clock.h`: mode/rate transaction and reply checks
- `endpoint.c`: mode selection before rate preparation in the Debian branch
- `stream.c`: defer probe-time hardware configuration while keeping descriptor/rate discovery

Preserve the target's UAC2, playback, stereo and four-byte/32-bit alternate checks. Choose native mode from the requested format, not the alternate's capability mask: the alternate is shared with PCM/DoP. Rewrite the rate after a mode change even if its numeric value is unchanged. Keep opt-out and other-device behavior intact.

Native transport rates are 88200/176400/352800; these are not DSD bit clocks. Do not change byte order, feedback scaling or prefill just to match another host's URB sizes.

## Build checks

Use matching headers, compiler, configuration and symbol versions. Update the exact checks in `build.sh` and `check_headers.py` only after reviewing those inputs. Ubuntu 24.04 HWE and Ubuntu 26.04 can share an ABI name while requiring different build inputs.

Run the offline tests with GCC sanitizer support:

```sh
ASAN_OPTIONS=detect_leaks=0 python3 -m unittest discover -s tests -v
```

Then build the complete module and test the port on its target hardware. There is no automatic DKMS rebuild.
