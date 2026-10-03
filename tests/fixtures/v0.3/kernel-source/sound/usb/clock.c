// SPDX-License-Identifier: GPL-2.0-or-later
/*
 * Fostex HP-A4BL native DSD modifications: 2026-10-02.
 * Historical v0.3 regression fixture; see docs/PROVENANCE.md.
 * This publication adds this notice only; executable logic is unchanged.
 */
/* Verbatim function extracts from experimental v0.3; regression fixture only. */
static int get_sample_rate_v2v3(struct snd_usb_audio *chip, int iface,
			      int altsetting, int clock)
{
	struct usb_device *dev = chip->dev;
	__le32 data;
	int err;
	struct usb_host_interface *ctrl_intf;

	ctrl_intf = snd_usb_find_ctrl_interface(chip, iface);
	err = snd_usb_ctl_msg(dev, usb_rcvctrlpipe(dev, 0), UAC2_CS_CUR,
			      USB_TYPE_CLASS | USB_RECIP_INTERFACE | USB_DIR_IN,
			      UAC2_CS_CONTROL_SAM_FREQ << 8,
			      snd_usb_ctrl_intf(ctrl_intf) | (clock << 8),
			      &data, sizeof(data));
	if (err < 0) {
		dev_warn(&dev->dev, "%d:%d: cannot get freq (v2/v3): err %d\n",
			 iface, altsetting, err);
		return 0;
	}

	return le32_to_cpu(data);
}
int snd_usb_set_sample_rate_v2v3(struct snd_usb_audio *chip,
				 const struct audioformat *fmt,
				 int clock, int rate)
{
	bool writeable;
	u32 bmControls;
	__le32 data;
	int err;
	union uac23_clock_source_desc *cs_desc;
	struct usb_host_interface *ctrl_intf;

	ctrl_intf = snd_usb_find_ctrl_interface(chip, fmt->iface);
	cs_desc = snd_usb_find_clock_source(chip, clock, fmt);

	if (!cs_desc)
		return 0;

	if (fmt->protocol == UAC_VERSION_3)
		bmControls = le32_to_cpu(cs_desc->v3.bmControls);
	else
		bmControls = cs_desc->v2.bmControls;

	writeable = uac_v2v3_control_is_writeable(bmControls,
						  UAC2_CS_CONTROL_SAM_FREQ);
	if (!writeable)
		return 0;

	data = cpu_to_le32(rate);
	err = snd_usb_ctl_msg(chip->dev, usb_sndctrlpipe(chip->dev, 0), UAC2_CS_CUR,
			      USB_TYPE_CLASS | USB_RECIP_INTERFACE | USB_DIR_OUT,
			      UAC2_CS_CONTROL_SAM_FREQ << 8,
			      snd_usb_ctrl_intf(ctrl_intf) | (clock << 8),
			      &data, sizeof(data));
	if (err < 0)
		return err;

	return get_sample_rate_v2v3(chip, fmt->iface, fmt->altsetting, clock);
}
static int set_sample_rate_v2v3(struct snd_usb_audio *chip,
				const struct audioformat *fmt, int rate)
{
	int cur_rate, prev_rate;
	int clock;

	/* First, try to find a valid clock. This may trigger
	 * automatic clock selection if the current clock is not
	 * valid.
	 */
	clock = snd_usb_clock_find_source(chip, fmt, true);
	if (clock < 0) {
		/* We did not find a valid clock, but that might be
		 * because the current sample rate does not match an
		 * external clock source. Try again without validation
		 * and we will do another validation after setting the
		 * rate.
		 */
		clock = snd_usb_clock_find_source(chip, fmt, false);

		/* Hardcoded sample rates */
		if (chip->quirk_flags & QUIRK_FLAG_IGNORE_CLOCK_SOURCE)
			return 0;

		if (clock < 0)
			return clock;
	}

	prev_rate = get_sample_rate_v2v3(chip, fmt->iface, fmt->altsetting, clock);
	if (prev_rate == rate)
		goto validation;

	cur_rate = snd_usb_set_sample_rate_v2v3(chip, fmt, clock, rate);
	if (cur_rate < 0) {
		usb_audio_err(chip,
			      "%d:%d: cannot set freq %d (v2/v3): err %d\n",
			      fmt->iface, fmt->altsetting, rate, cur_rate);
		return cur_rate;
	}

	if (!cur_rate)
		cur_rate = prev_rate;

	if (cur_rate != rate) {
		usb_audio_dbg(chip,
			      "%d:%d: freq mismatch: req %d, clock runs @%d\n",
			      fmt->iface, fmt->altsetting, rate, cur_rate);
		/* continue processing */
	}

	/* FIXME - TEAC devices require the immediate interface setup */
	if (USB_ID_VENDOR(chip->usb_id) == 0x0644) {
		bool cur_base_48k = (rate % 48000 == 0);
		bool prev_base_48k = (prev_rate % 48000 == 0);
		if (cur_base_48k != prev_base_48k) {
			usb_set_interface(chip->dev, fmt->iface, fmt->altsetting);
			if (chip->quirk_flags & QUIRK_FLAG_IFACE_DELAY)
				msleep(50);
		}
	}

validation:
	/* validate clock after rate change */
	if (!uac_clock_source_is_valid(chip, fmt, clock))
		return -ENXIO;
	return 0;
}
