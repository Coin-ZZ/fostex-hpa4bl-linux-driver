# Build, load and rollback

Use a [listed kernel](../README.md#compatibility) with matching headers, compiler, make and Python 3. As an ordinary user:

```sh
sha256sum -c SHA256SUMS
sh build.sh "/lib/modules/$(uname -r)/build"
```

The output is `kernel-source/sound/usb/snd-usb-audio.ko` on Ubuntu, or `kernel-source-debian-6.12/sound/usb/snd-usb-audio.ko` on Debian. Set `KO` to that file's absolute path. The script only builds the module.

If signature enforcement is enabled, sign it through your distribution's existing process using an already trusted local key. Keep Secure Boot enabled and keys private; do not bypass signature errors.

## Temporary load

Record the stock identity with `modinfo snd_usb_audio` and `/sys/module/snd_usb_audio/srcversion`. Leave the stock module files and boot configuration unchanged.

Stop applications using any USB audio device, since replacing `snd_usb_audio` affects all of them. Lower physical volume before playback; do not rely on software DSD attenuation.

Run these commands individually, stopping on failure:

```sh
sudo modprobe snd_usb_audio
sudo rmmod snd_usb_audio
sudo insmod "${KO:?set KO to the built and, if required, signed module}" fostex_dsd=1
cat /sys/module/snd_usb_audio/parameters/fostex_dsd
cat /sys/module/snd_usb_audio/srcversion
modinfo -F srcversion "$KO"
```

The parameter should read `Y`, and the loaded source version should match the file. If insertion fails, restore the stock driver with `sudo modprobe snd_usb_audio`. Never force loading or unloading. If busy, stop its users first.

## Playback

Select the HP-A4BL ALSA hardware device in a native-DSD-capable player. Use `DSD_U32_BE` at transport rates 88200, 176400 or 352800 for DSD64, DSD128 or DSD256 respectively.

For raw playback, each stereo frame is four chronological MSB-first bytes for the left channel followed by four for the right. DSF/DFF containers must be decoded first.

## Rollback

Stop playback, lower physical volume, then:

```sh
sudo rmmod snd_usb_audio
sudo modprobe snd_usb_audio
```

Verify the saved stock identity and restart the applications you stopped. If the module cannot be safely unloaded, rebooting restores the stock driver when its files and boot configuration were left unchanged. This procedure does not install persistently or configure DKMS.
