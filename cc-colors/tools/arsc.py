#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""resources.arsc 解析器 v2: 支持 sparse/offset16 type chunk + config 限定符
用法:
  python arsc.py <apk> list <关键字>              # 列出名字含关键字的 dimen: 值 + 配置
  python arsc.py <apk> set <名字> <N>dp --config <密度匹配子串>   # 只改配置匹配的条目(可省略=全部)
"""
import struct, sys, zipfile

def u16(b, o): return struct.unpack_from('<H', b, o)[0]
def u32(b, o): return struct.unpack_from('<I', b, o)[0]

def parse_string_pool(b, off):
    count = u32(b, off + 8)
    flags = u32(b, off + 16)
    stringsStart = u32(b, off + 20)
    is_utf8 = bool(flags & 0x100)
    offsets_off = off + 28
    out = []
    for i in range(count):
        p = off + stringsStart + u32(b, offsets_off + i * 4)
        if is_utf8:
            def varint(o):
                v = b[o]
                if v & 0x80:
                    return ((v & 0x7F) << 8) | b[o + 1], o + 2
                return v, o + 1
            _, q = varint(p)
            ln, q3 = varint(q)
            out.append(b[q3:q3 + ln].decode('utf-8', 'replace'))
        else:
            def varint16(o):
                v = u16(b, o)
                if v & 0x8000:
                    return ((v & 0x7FFF) << 16) | u16(b, o + 2), o + 4
                return v, o + 2
            n, q = varint16(p)
            out.append(b[q:q + n * 2].decode('utf-16-le', 'replace'))
    return out

def decode_config(b, cfg_off):
    """ResTable_config: size@0 mcc@4 mnc@6 lang@8 country@10 orient@12 touch@13 density@14
    keyboard@16 nav@17 inputFlags@18 screenW@20 screenH@22 sdk@24 minor@26
    screenLayout@28 uiMode@29 smallestW@30 screenWdp@32 screenHdp@34"""
    size = u32(b, cfg_off)
    density = u16(b, cfg_off + 14)
    orientation = b[cfg_off + 12]
    screenWidth = u16(b, cfg_off + 20)
    screenHeight = u16(b, cfg_off + 22)
    screenLayout = b[cfg_off + 28] if size >= 32 else 0
    uiMode = b[cfg_off + 29] if size >= 32 else 0
    smallestW = u16(b, cfg_off + 30) if size >= 32 else 0
    screenWdp = u16(b, cfg_off + 32) if size >= 36 else 0
    screenHdp = u16(b, cfg_off + 34) if size >= 36 else 0
    parts = []
    ormap = {1: 'port', 2: 'land', 3: 'square'}
    if orientation in ormap: parts.append(ormap[orientation])
    if density not in (0, 0xFFFE, 0xFFFF): parts.append('%ddpi' % density)
    sl = screenLayout & 0x0F
    if sl: parts.append({1: 'small', 2: 'normal', 3: 'large', 4: 'xlarge'}.get(sl, 'sz%d' % sl))
    if screenLayout & 0x20: parts.append('long')
    un = (uiMode & 0x30)
    if un == 0x20: parts.append('night')
    um = uiMode & 0x0F
    if um: parts.append({1: 'car', 2: 'desk', 3: 'tv', 4: 'watch', 6: 'vr'}.get(um, 'ui%d' % um))
    if smallestW: parts.append('sw%ddp' % smallestW)
    if screenWdp: parts.append('w%ddp-h%ddp' % (screenWdp, screenHdp))
    if screenWidth: parts.append('%dx%d' % (screenWidth, screenHeight))
    return '/'.join(parts) if parts else 'default'

def parse(arsc):
    b = arsc
    table_hs = u16(b, 2)
    pool_off = table_hs
    pkg_off = pool_off + u32(b, pool_off + 4)
    results = []  # dict
    while pkg_off < len(b) - 8:
        ctype = u16(b, pkg_off)
        csize = u32(b, pkg_off + 4)
        if ctype == 0x0200:
            typeStrings = u32(b, pkg_off + 268)
            keyStrings = u32(b, pkg_off + 276)
            tstr = parse_string_pool(b, pkg_off + typeStrings)
            kstr = parse_string_pool(b, pkg_off + keyStrings)
            sub = pkg_off + u16(b, pkg_off + 2)
            end = pkg_off + csize
            while sub < end - 8:
                stype = u16(b, sub)
                shsize = u16(b, sub + 2)
                ssize = u32(b, sub + 4)
                if stype == 0x0201:
                    tid = b[sub + 8]
                    tflags = u16(b, sub + 10)
                    entryCount = u32(b, sub + 12)
                    entriesStart = u32(b, sub + 16)
                    tname = tstr[tid - 1] if 0 < tid <= len(tstr) else str(tid)
                    cfg = decode_config(b, sub + 20)
                    sparse = bool(tflags & 0x01)
                    off16 = bool(tflags & 0x02)
                    for i in range(entryCount):
                        if sparse:
                            base = sub + shsize + i * 4
                            key = u16(b, base)
                            raw = u16(b, base + 2)
                            if raw == 0xFFFF: continue
                            eoff = raw * 4
                        elif off16:
                            base = sub + shsize + i * 2
                            key = i
                            raw = u16(b, base)
                            if raw == 0xFFFF: continue
                            eoff = raw * 4
                        else:
                            key = i
                            eoff = u32(b, sub + shsize + i * 4)
                            if eoff == 0xFFFFFFFF: continue
                        eabs = sub + entriesStart + eoff
                        esize = u16(b, eabs)
                        eflags = u16(b, eabs + 2)
                        rkey = u32(b, eabs + 4)
                        if rkey >= len(kstr): continue
                        if eflags & 1: continue
                        voff = eabs + esize
                        if voff + 8 > len(b): continue
                        results.append(dict(name=kstr[rkey], tname=tname, cfg=cfg,
                                            eabs=eabs, doff=voff + 4,
                                            dtype=b[voff + 3], data=u32(b, voff + 4)))
                sub += ssize
        pkg_off += csize
    return results

def fmt_dimen(data):
    u = {1: 'dp', 0: 'px', 2: 'sp', 3: 'pt', 4: 'in', 5: 'mm'}.get(data & 0xF, 'u%d' % (data & 0xF))
    radix = (data >> 4) & 0x3
    mant = data >> 8
    v = {1: mant / 2.0, 2: mant / 16.0, 3: mant / 128.0}.get(radix, mant)
    return '%s%s' % (v, u)

def main():
    src, mode = sys.argv[1], sys.argv[2]
    z = zipfile.ZipFile(src)
    arsc = bytearray(z.read('resources.arsc'))
    results = parse(bytes(arsc))
    if mode == 'list':
        kw = sys.argv[3].lower()
        for r in results:
            if r['tname'] == 'dimen' and kw in r['name'].lower():
                v = fmt_dimen(r['data']) if r['dtype'] == 5 else 'type=%d' % r['dtype']
                print('%-50s %-10s %s' % (r['name'], v, r['cfg']))
    elif mode == 'set':
        name, val = sys.argv[3], sys.argv[4]
        cfgkw = ''
        if '--config' in sys.argv:
            cfgkw = sys.argv[sys.argv.index('--config') + 1].lower()
        n = int(val.rstrip('dp'))
        newdata = (n << 8) | 1
        cnt = 0
        for r in results:
            if r['tname'] == 'dimen' and r['name'] == name and r['dtype'] == 5 \
               and (not cfgkw or cfgkw in r['cfg'].lower()):
                struct.pack_into('<I', arsc, r['doff'], newdata)
                cnt += 1
                print('patched %s [%s]: %s -> %ddp' % (name, r['cfg'], fmt_dimen(r['data']), n))
        if cnt == 0:
            print('!! 没有匹配条目'); sys.exit(1)
        outapk = src.replace('.apk', '.patched.apk')
        zout = zipfile.ZipFile(outapk, 'w', zipfile.ZIP_DEFLATED)
        for item in z.infolist():
            if item.filename == 'resources.arsc':
                zout.writestr(item, bytes(arsc))
            else:
                zout.writestr(item, z.read(item.filename))
        zout.close()
        print('OK -> %s (%d 处)' % (outapk, cnt))

if __name__ == '__main__':
    main()
