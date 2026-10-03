# fostex-hpa4bl-linux-driver

[简体中文](README.zh-CN.md)

Linux `snd-usb-audio` driver with native DSD64/128/256 support for the Fostex HP-A4BL (`1019:0013`). Unofficial, source only. Enable the Fostex changes with `fostex_dsd=1`; they are off by default.

## Compatibility

- Ubuntu 24.04 HWE, `7.0.0-34-generic`, GCC 13: built and tested on an HP-A4BL with PCM and native DSD64/128/256
- Debian `6.12.107+deb13-amd64`, GCC 14: built and tested offline; no hardware test
- Ubuntu 26.04: an existing build check is included, but this driver revision was not rebuilt or hardware-tested there

Other kernels require [porting](docs/PORTING.md).

## Build

Install matching kernel headers, the compiler, make and Python 3, then run:

```sh
sh build.sh "/lib/modules/$(uname -r)/build"
```

[Loading and rollback](docs/INSTALL.md) · [Porting](docs/PORTING.md) · [Source and license](docs/PROVENANCE.md)

GPLv2; original helper tools use the license in `LICENSE-tools`.
