// SPDX-License-Identifier: GPL-2.0-or-later
/*
 * Fostex HP-A4BL native DSD modifications: 2026-10-02.
 * Historical v0.3 regression fixture; see docs/PROVENANCE.md.
 * This publication adds this notice only; executable logic is unchanged.
 */
/* Verbatim function extracts from experimental v0.3; regression fixture only. */
static bool is_fostex_dsd(const struct snd_usb_audio *chip)
{
	return fostex_dsd && chip->usb_id == USB_ID(0x1019, 0x0013);
}
int snd_usb_select_mode_quirk(struct snd_usb_audio *chip,
			      const struct audioformat *fmt,
			      snd_pcm_format_t selected_format)
{
	struct usb_device *dev = chip->dev;
	int err;
	u16 mode_iface = is_fostex_dsd(chip) ? fmt->iface : 1;

	if ((chip->quirk_flags & QUIRK_FLAG_ITF_USB_DSD_DAC) ||
	    is_fostex_dsd(chip)) {
		/* First switch to alt set 0, otherwise the mode switch cmd
		 * will not be accepted by the DAC
		 */
		err = usb_set_interface(dev, fmt->iface, 0);
		if (err < 0)
			return err;

		msleep(20); /* Delay needed after setting the interface */

		/* Vendor mode switch cmd is required. */
		/* Fostex shares the 32-bit alternate with PCM/DoP. */
		if (is_fostex_dsd(chip) ?
		    selected_format == SNDRV_PCM_FORMAT_DSD_U32_BE :
		    !!(fmt->formats & SNDRV_PCM_FMTBIT_DSD_U32_BE)) {
			/* DSD mode (DSD_U32) requested */
			err = snd_usb_ctl_msg(dev, usb_sndctrlpipe(dev, 0), 0,
					      USB_DIR_OUT|USB_TYPE_VENDOR|USB_RECIP_INTERFACE,
					      1, mode_iface, NULL, 0);
			if (err < 0)
				return err;

		} else {
			/* PCM or DOP mode (S32) requested */
			/* PCM mode (S16) requested */
			err = snd_usb_ctl_msg(dev, usb_sndctrlpipe(dev, 0), 0,
					      USB_DIR_OUT|USB_TYPE_VENDOR|USB_RECIP_INTERFACE,
					      0, mode_iface, NULL, 0);
			if (err < 0)
				return err;

		}
		msleep(20);
	}
	return 0;
}
