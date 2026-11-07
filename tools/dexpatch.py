#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Patch bytes inside a .dex stored in an APK, then repair the dex checksum/signature
and rebuild the APK while preserving each entry's original compression type.

Usage:
    python dexpatch.py <apk> <dex-name> <file-offset> <old-hex> <new-hex> [-o out.apk]

Example (HyperOS control-center plugin, card icon size):
    python dexpatch.py base.apk classes2.dex 0x1aedc4 60014936 60018631 -o base.patched.apk

Notes:
    * offset is the byte offset inside the dex file (not the APK).
    * old-hex must match exactly, otherwise nothing is written (safety).
    * dex header: checksum(Adler-32 over bytes[12:]) @8, signature(SHA-1 over bytes[32:]) @12.
"""
import argparse
import hashlib
import struct
import sys
import zipfile
import zlib


def read_dex(apk_path, dex_name):
    with zipfile.ZipFile(apk_path) as z:
        return bytearray(z.read(dex_name)), z


def patch_dex(dex, offset, old, new):
    actual = bytes(dex[offset:offset + len(old)])
    if actual != old:
        raise SystemExit('patch site mismatch: expected %s, found %s at 0x%x'
                         % (old.hex(), actual.hex(), offset))
    if len(old) != len(new):
        raise SystemExit('old and new must be the same length (in-place patch)')
    dex[offset:offset + len(new)] = new


def fix_header(dex):
    # signature = SHA-1 of bytes[32:]
    dex[12:32] = hashlib.sha1(bytes(dex[32:])).digest()
    # checksum = Adler-32 of bytes[12:], little-endian @ offset 8
    chk = zlib.adler32(bytes(dex[12:])) & 0xFFFFFFFF
    struct.pack_into('<I', dex, 8, chk)
    return chk


def rebuild_apk(z, dex_name, dex_bytes, out_path):
    with zipfile.ZipFile(out_path, 'w') as zo:
        for info in z.infolist():
            data = bytes(dex_bytes) if info.filename == dex_name else z.read(info.filename)
            zi = zipfile.ZipInfo(info.filename, date_time=info.date_time)
            zi.compress_type = info.compress_type
            zi.external_attr = info.external_attr
            zi.internal_attr = info.internal_attr
            zi.create_system = info.create_system
            zo.writestr(zi, data)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('apk')
    ap.add_argument('dex')
    ap.add_argument('offset', type=lambda s: int(s, 0))
    ap.add_argument('old_hex')
    ap.add_argument('new_hex')
    ap.add_argument('-o', '--out')
    args = ap.parse_args()

    old = bytes.fromhex(args.old_hex)
    new = bytes.fromhex(args.new_hex)

    dex, z = read_dex(args.apk, args.dex)
    print('dex %s: %d bytes' % (args.dex, len(dex)))
    print('before: %s' % bytes(dex[args.offset:args.offset + len(old)]).hex())

    patch_dex(dex, args.offset, old, new)
    print('after : %s' % bytes(dex[args.offset:args.offset + len(new)]).hex())

    chk = fix_header(dex)
    print('new checksum: 0x%08x' % chk)

    out = args.out or args.apk.replace('.apk', '.patched.apk')
    rebuild_apk(z, args.dex, dex, out)
    print('wrote %s' % out)
    print('remember: zipalign -f 4 %s <aligned.apk> before installing' % out)


if __name__ == '__main__':
    main()
