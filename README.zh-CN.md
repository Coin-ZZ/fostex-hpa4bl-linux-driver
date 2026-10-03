# fostex-hpa4bl-linux-driver

[English](README.md)

为 Fostex HP-A4BL（`1019:0013`）提供 Native DSD64/128/256 支持的 Linux `snd-usb-audio` 驱动。非官方项目，仅提供源码。Fostex 修改默认关闭，通过 `fostex_dsd=1` 启用。

## 适用范围

- Ubuntu 24.04 HWE，`7.0.0-34-generic`，GCC 13：已编译，并在 HP-A4BL 上实测 PCM 和 Native DSD64/128/256
- Debian `6.12.107+deb13-amd64`，GCC 14：已编译及离线测试，未做硬件实测
- Ubuntu 26.04：包含已有的构建检查，但本版驱动未在该系统重新编译或实测

其他内核需要[移植](docs/PORTING.md)。

## 编译

准备匹配的内核头文件、编译器、make 和 Python 3，然后运行：

```sh
sh build.sh "/lib/modules/$(uname -r)/build"
```

[加载与回退](docs/INSTALL.md) · [移植说明](docs/PORTING.md) · [源码与许可](docs/PROVENANCE.md)

驱动使用 GPLv2；原创辅助工具的许可见 `LICENSE-tools`。
