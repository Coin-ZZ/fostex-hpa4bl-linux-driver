#!/usr/bin/env python3
"""Offline read-only TI C55x 0x09AA boot-table parser. Not a flasher or driver."""
import argparse
import hashlib
import json
from pathlib import Path


def parse_boot(data):
    def integer(offset, size):
        if offset < 0 or offset + size > len(data):
            raise ValueError(f'truncated field at {offset:#x}')
        return int.from_bytes(data[offset:offset + size], 'big')
    if integer(0, 2) != 0x09aa:
        raise ValueError('not an unencrypted TI C55x 0x09AA boot image')
    entry = integer(2, 4)
    count = integer(6, 2)
    regs = [{'address': integer(8 + 4*i, 2), 'value': integer(10 + 4*i, 2)} for i in range(count)]
    sections = []
    offset = 8 + count*4
    while True:
        words = integer(offset, 2)
        if words == 0:
            if offset + 2 != len(data):
                raise ValueError(f'{len(data)-offset-2} unparsed bytes after terminator')
            return {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data),
                    'format': 'TI C55x unencrypted boot table (0x09AA)',
                    'entry_byte_address': entry, 'register_configuration': regs,
                    'sections': sections, 'terminator_offset': offset}
        address = integer(offset+2,4)
        payload_offset = offset+6
        padded = ((words + 2 + 3)//4)*8
        following = offset+2+padded
        if following > len(data):
            raise ValueError(f'truncated section at {offset:#x}')
        payload = data[payload_offset:payload_offset+2*words]
        sections.append({'file_offset': offset, 'data_offset': payload_offset,
                         'word_address': address, 'words': words,
                         'payload_sha256': hashlib.sha256(payload).hexdigest()})
        offset = following


def word_bytes(data):
    """Convert a TI char array only if every big-endian 16-bit word fits uint8."""
    if len(data)%2:
        raise ValueError('unaligned word array')
    if any(data[::2]):
        raise ValueError('not a byte-per-word array')
    return data[1::2]


def parse_cinit(data):
    """C55x COFF .cinit records, SPRU281G 6.9.1.1; never execute records."""
    offset=0
    result=[]
    while offset+2<=len(data):
        words=int.from_bytes(data[offset:offset+2],'big')
        if not words:
            if offset+2!=len(data):
                raise ValueError('trailing cinit data')
            return result
        if words & 0xc000 or offset+6+2*words>len(data):
            raise ValueError(f'invalid cinit record at {offset:#x}')
        addr=int.from_bytes(data[offset+2:offset+5],'big')
        flags=data[offset+5]
        if flags & ~1:
            raise ValueError('reserved cinit flags set')
        result.append({'offset':offset,'words':words,'word_address':addr,'io_space':bool(flags&1),
                       'data_offset':offset+6})
        offset+=6+2*words
    raise ValueError('missing cinit terminator')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('image',type=Path)
    args=ap.parse_args()
    try:
        result=parse_boot(args.image.read_bytes())
    except (OSError, ValueError) as exc:
        ap.error(str(exc))
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
