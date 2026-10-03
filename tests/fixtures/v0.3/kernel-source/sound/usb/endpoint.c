// SPDX-License-Identifier: GPL-2.0-or-later
/*
 * Fostex HP-A4BL native DSD modifications: 2026-10-02.
 * Historical v0.3 regression fixture; see docs/PROVENANCE.md.
 * This publication adds this notice only; executable logic is unchanged.
 */
/* Verbatim function extracts from experimental v0.3; regression fixture only. */
static int update_clock_ref_rate(struct snd_usb_audio *chip,
				 struct snd_usb_endpoint *ep)
{
	struct snd_usb_clock_ref *clock = ep->clock_ref;
	int rate = ep->cur_rate;

	if (!clock || clock->rate == rate)
		return rate;
	if (clock->rate) {
		if (atomic_read(&clock->locked))
			return clock->rate;
		if (clock->rate != rate) {
			usb_audio_err(chip, "Mismatched sample rate %d vs %d for EP 0x%x\n",
				      clock->rate, rate, ep->ep_num);
			return clock->rate;
		}
	}
	clock->rate = rate;
	clock->need_setup = true;
	return rate;
}
static int init_sample_rate(struct snd_usb_audio *chip,
			    struct snd_usb_endpoint *ep)
{
	struct snd_usb_clock_ref *clock = ep->clock_ref;
	int rate, err;

	rate = update_clock_ref_rate(chip, ep);
	if (rate < 0)
		return rate;
	if (clock && !clock->need_setup)
		return 0;

	if (!ep->fixed_rate) {
		err = snd_usb_init_sample_rate(chip, ep->cur_audiofmt, rate);
		if (err < 0) {
			if (clock)
				clock->rate = 0; /* reset rate */
			return err;
		}
	}

	if (clock)
		clock->need_setup = false;
	return 0;
}
int snd_usb_endpoint_prepare(struct snd_usb_audio *chip,
			     struct snd_usb_endpoint *ep)
{
	bool iface_first;
	int err = 0;

	guard(mutex)(&chip->mutex);
	if (WARN_ON(!ep->iface_ref))
		return 0;
	if (!ep->need_prepare)
		return 0;

	/* If the interface has been already set up, just set EP parameters */
	if (!ep->iface_ref->need_setup) {
		/* sample rate setup of UAC1 is per endpoint, and we need
		 * to update at each EP configuration
		 */
		if (ep->cur_audiofmt->protocol == UAC_VERSION_1) {
			err = init_sample_rate(chip, ep);
			if (err < 0)
				return err;
		}
		goto done;
	}

	/* Need to deselect altsetting at first */
	endpoint_set_interface(chip, ep, false);

	/* Some UAC1 devices (e.g. Yamaha THR10) need the host interface
	 * to be set up before parameter setups
	 */
	iface_first = ep->cur_audiofmt->protocol == UAC_VERSION_1;
	/* Workaround for devices that require the interface setup at first like UAC1 */
	if (chip->quirk_flags & QUIRK_FLAG_SET_IFACE_FIRST)
		iface_first = true;
	if (iface_first) {
		err = endpoint_set_interface(chip, ep, true);
		if (err < 0)
			return err;
	}

	err = snd_usb_select_mode_quirk(chip, ep->cur_audiofmt,
					ep->cur_format);
	if (err < 0)
		return err;

	err = snd_usb_init_pitch(chip, ep->cur_audiofmt);
	if (err < 0)
		return err;

	err = init_sample_rate(chip, ep);
	if (err < 0)
		return err;

	/* for UAC2/3, enable the interface altset here at last */
	if (!iface_first) {
		err = endpoint_set_interface(chip, ep, true);
		if (err < 0)
			return err;
	}

	ep->iface_ref->need_setup = false;

 done:
	ep->need_prepare = false;
	return 1;
}
