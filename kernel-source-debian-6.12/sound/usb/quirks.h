/*
 * Fostex HP-A4BL native DSD modifications: 2026-10-02.
 * Local driver changes; see docs/PROVENANCE.md.
 * This publication adds this notice only; executable logic is unchanged.
 */
/* SPDX-License-Identifier: GPL-2.0 */
#ifndef __USBAUDIO_QUIRKS_H
#define __USBAUDIO_QUIRKS_H

#include <sound/pcm.h>

struct audioformat;
struct snd_usb_endpoint;
struct snd_usb_substream;

int snd_usb_create_quirk(struct snd_usb_audio *chip,
			 struct usb_interface *iface,
			 struct usb_driver *driver,
			 const struct snd_usb_audio_quirk *quirk);

int snd_usb_apply_interface_quirk(struct snd_usb_audio *chip,
				  int iface,
				  int altno);

int snd_usb_apply_boot_quirk(struct usb_device *dev,
			     struct usb_interface *intf,
			     const struct snd_usb_audio_quirk *quirk,
			     unsigned int usb_id);

int snd_usb_apply_boot_quirk_once(struct usb_device *dev,
				  struct usb_interface *intf,
				  const struct snd_usb_audio_quirk *quirk,
				  unsigned int usb_id);

void snd_usb_set_format_quirk(struct snd_usb_substream *subs,
			      const struct audioformat *fmt);

int snd_usb_is_big_endian_format(struct snd_usb_audio *chip,
				 const struct audioformat *fp);

void snd_usb_endpoint_start_quirk(struct snd_usb_endpoint *ep);

void snd_usb_ctl_msg_quirk(struct usb_device *dev, unsigned int pipe,
			   __u8 request, __u8 requesttype, __u16 value,
			   __u16 index, void *data, __u16 size);

/* True only for explicitly enabled native DSD on HP-A4BL 1019:0013. */
bool snd_usb_fostex_dsd_enabled(struct snd_usb_audio *chip);

/* Returns 1 when the Fostex quirk fully initialized the clock, 0 otherwise. */
int snd_usb_select_mode_quirk(struct snd_usb_audio *chip,
			      const struct audioformat *fmt,
			      snd_pcm_format_t selected_format,
			      unsigned int selected_rate);

u64 snd_usb_interface_dsd_format_quirks(struct snd_usb_audio *chip,
					struct audioformat *fp,
					unsigned int sample_bytes);

void snd_usb_audioformat_attributes_quirk(struct snd_usb_audio *chip,
					  struct audioformat *fp,
					  int stream);

void snd_usb_init_quirk_flags(struct snd_usb_audio *chip);

#endif /* __USBAUDIO_QUIRKS_H */
