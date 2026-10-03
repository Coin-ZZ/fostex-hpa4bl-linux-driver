/*
 * Fostex HP-A4BL native DSD modifications: 2026-10-02.
 * Local driver changes; see docs/PROVENANCE.md.
 * This publication adds this notice only; executable logic is unchanged.
 */
/* SPDX-License-Identifier: GPL-2.0 */
#ifndef __USBAUDIO_CLOCK_H
#define __USBAUDIO_CLOCK_H

int snd_usb_init_sample_rate(struct snd_usb_audio *chip,
			     const struct audioformat *fmt, int rate);

int snd_usb_clock_find_source(struct snd_usb_audio *chip,
			      const struct audioformat *fmt, bool validate);

int snd_usb_set_sample_rate_v2v3(struct snd_usb_audio *chip,
				 const struct audioformat *fmt,
				 int clock, int rate);

int snd_usb_fostex_set_rate(struct snd_usb_audio *chip,
			    const struct audioformat *fmt, int clock, int rate);

#endif /* __USBAUDIO_CLOCK_H */
