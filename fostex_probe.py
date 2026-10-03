#!/usr/bin/env python3
"""Read-only Fostex USB/ALSA evidence collector. Never opens /dev or writes sysfs."""
import argparse
import json
import platform
import re
from pathlib import Path


def read_text(path):
    try:
        return path.read_text(errors='replace').strip()
    except (OSError, ValueError):
        return None


def descriptors(data):
    """Decode USB descriptors, retaining raw bytes and unambiguous UAC2 fields."""
    out = []
    offset = 0
    interface = None
    while offset < len(data):
        if len(data) - offset < 2:
            raise ValueError(f'truncated descriptor header at {offset}')
        length, dtype = data[offset:offset + 2]
        if length < 2 or offset + length > len(data):
            raise ValueError(f'invalid descriptor length {length} at {offset}')
        d = data[offset:offset + length]
        row = {'offset': offset, 'type': dtype, 'length': length, 'hex': d.hex()}
        if dtype == 1 and length >= 18:
            row.update(vid=f'{int.from_bytes(d[8:10], "little"):04x}',
                       pid=f'{int.from_bytes(d[10:12], "little"):04x}',
                       bcd_device=f'{int.from_bytes(d[12:14], "little"):04x}')
        elif dtype == 4 and length >= 9:
            interface = {'number': d[2], 'alternate': d[3], 'class': d[5],
                         'subclass': d[6], 'protocol': d[7]}
            row['interface'] = dict(interface)
        elif dtype == 5 and length >= 7:
            row['endpoint'] = {'address': d[2], 'attributes': d[3],
                               'max_packet_size_raw': int.from_bytes(d[4:6], 'little'),
                               'interval': d[6]}
            row['interface'] = interface
        elif dtype == 0x24 and interface:
            row['interface'] = dict(interface)
            if interface['class'] == 1 and interface['subclass'] == 2 and interface['protocol'] == 0x20:
                if length >= 16 and d[2] == 1:
                    formats = int.from_bytes(d[6:10], 'little')
                    row['uac2_streaming'] = {'terminal_link': d[3], 'format_type': d[5],
                                             'formats_bitmap': formats, 'pcm_advertised': bool(formats & 1),
                                             'raw_data_advertised': bool(formats & 0x80000000),
                                             'channels': d[10]}
                elif length >= 6 and d[2] == 2 and d[3] == 1:
                    row['uac2_type_i'] = {'subslot_bytes': d[4], 'resolution_bits': d[5]}
        out.append(row)
        offset += length
    return out


def collect(root):
    usb_root = root / 'sys/bus/usb/devices'
    cards_root = root / 'proc/asound'
    result = {'schema': 1, 'kernel': platform.release(), 'hardware_verified': False,
              'policy': 'Read existing sysfs and procfs only; no USB control transfers, playback, firmware, or configuration writes.',
              'devices': [], 'alsa_cards': read_text(cards_root / 'cards')}
    for dev in sorted(usb_root.glob('*')):
        vid, pid = read_text(dev / 'idVendor'), read_text(dev / 'idProduct')
        product = read_text(dev / 'product') or ''
        manufacturer = read_text(dev / 'manufacturer') or ''
        if not vid or not pid or not (('FOSTEX' in (product + manufacturer).upper()) or
                                      (vid.lower(), pid.lower()) == ('1019', '0013')):
            continue
        item = {'usb_path': dev.name, 'vid': vid, 'pid': pid, 'product': product,
                'manufacturer': manufacturer, 'bcd_device': read_text(dev / 'bcdDevice'), 'firmware_version': 'unknown',
                'speed_mbps': read_text(dev / 'speed'), 'interfaces': [], 'alsa': []}
        try:
            item['descriptors'] = descriptors((dev / 'descriptors').read_bytes())
        except (OSError, ValueError) as exc:
            item['descriptor_error'] = str(exc)
        for intf in sorted(usb_root.glob(dev.name + ':*')):
            driver = intf / 'driver'
            item['interfaces'].append({'name': intf.name, 'driver': driver.resolve().name if driver.is_symlink() else None,
                                      'class': read_text(intf / 'bInterfaceClass'),
                                      'subclass': read_text(intf / 'bInterfaceSubClass'),
                                      'protocol': read_text(intf / 'bInterfaceProtocol')})
        for card in sorted((root / 'sys/class/sound').glob('card*')):
            # Resolve device ancestry instead of inferring identity from card names.
            target = (card / 'device').resolve()
            if dev.resolve() not in [target, *target.parents]:
                continue
            name = card.name
            if not re.fullmatch(r'card\d+', name):
                continue
            number = int(name[4:])
            proc = cards_root / name
            item['alsa'].append({'card_number': number, 'card_id': read_text(proc / 'id'),
                                 'streams': {p.name: read_text(p) for p in sorted(proc.glob('stream*'))}})
        result['devices'].append(item)
    if not result['devices']:
        result['status'] = 'No Fostex-labelled USB device found. This does not prove the device or driver is unsupported.'
    else:
        result['status'] = 'Evidence collected; descriptor/driver presence is not a playback test.'
    return result


def pcm_config(card_id):
    if not re.fullmatch(r'[A-Za-z0-9_]+', card_id):
        raise ValueError('ALSA card ID must contain only letters, digits and underscore')
    return f'''# Optional ALSA PCM profile, not a kernel driver. No default-device override.
# Fixed 48 kHz / 32-bit-container stereo standard PCM avoids advertised >192 kHz modes.
# Include this file from ~/.asoundrc only after verifying the card identity.
pcm.fostex_safe {{
    type plug
    slave {{
        pcm "hw:CARD={card_id},DEV=0"
        rate 48000
        format S32_LE
        channels 2
    }}
}}
ctl.fostex_safe {{
    type hw
    card "{card_id}"
}}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('/'), help='Filesystem root; fixtures may be inspected offline')
    parser.add_argument('--decode', type=Path, help='Decode a saved raw descriptor file offline')
    parser.add_argument('--pcm-config', metavar='ALSA_CARD_ID', help='Print optional safe PCM ALSA configuration; does not install it')
    args = parser.parse_args()
    if args.pcm_config:
        try:
            print(pcm_config(args.pcm_config), end='')
        except ValueError as exc:
            parser.error(str(exc))
    elif args.decode:
        try:
            print(json.dumps(descriptors(args.decode.read_bytes()), indent=2))
        except (OSError, ValueError) as exc:
            parser.error(str(exc))
    else:
        print(json.dumps(collect(args.root), indent=2, ensure_ascii=False))

if __name__ == '__main__':
    main()
