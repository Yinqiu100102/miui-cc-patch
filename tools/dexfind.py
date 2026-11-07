import sys, struct, zipfile

def uleb(b, o):
    r = 0; s = 0
    while True:
        x = b[o]; o += 1
        r |= (x & 0x7F) << s
        if not (x & 0x80):
            break
        s += 7
    return r, o

def strings(d):
    n = struct.unpack_from('<I', d, 0x38)[0]
    off = struct.unpack_from('<I', d, 0x3C)[0]
    out = []
    for i in range(n):
        p = struct.unpack_from('<I', d, off + i * 4)[0]
        ln, q = uleb(d, p)
        out.append(d[q:q + ln].decode('utf-8', 'replace'))
    return out

def types(d, st):
    n = struct.unpack_from('<I', d, 0x40)[0]
    off = struct.unpack_from('<I', d, 0x44)[0]
    return [st[struct.unpack_from('<I', d, off + i * 4)[0]] for i in range(n)]

def methods(d, st, ty):
    n = struct.unpack_from('<I', d, 0x58)[0]
    off = struct.unpack_from('<I', d, 0x5C)[0]
    out = []
    for i in range(n):
        cls_idx, proto_idx, name_idx = struct.unpack_from('<HHI', d, off + i * 8)
        out.append((ty[cls_idx], st[name_idx]))
    return out

def code_ranges(d, st, ty):
    """return list of (start, end, class, method)"""
    cn = struct.unpack_from('<I', d, 0x60)[0]
    coff = struct.unpack_from('<I', d, 0x64)[0]
    meth = methods(d, st, ty)
    res = []
    for i in range(cn):
        base = coff + i * 32
        class_idx = struct.unpack_from('<I', d, base)[0]
        class_data_off = struct.unpack_from('<I', d, base + 24)[0]
        cname = ty[class_idx]
        if class_data_off == 0:
            continue
        o = class_data_off
        sf, o = uleb(d, o)
        inf, o = uleb(d, o)
        dm, o = uleb(d, o)
        vm, o = uleb(d, o)
        for _ in range(sf + inf):
            _, o = uleb(d, o)
            _, o = uleb(d, o)
        for count in (dm, vm):
            idx = 0
            for _ in range(count):
                diff, o = uleb(d, o)
                idx += diff
                acc, o = uleb(d, o)
                code_off, o = uleb(d, o)
                if code_off == 0:
                    continue
                insns_size = struct.unpack_from('<I', d, code_off + 12)[0]
                start = code_off + 16
                end = start + insns_size * 2
                mname = meth[idx][1] if idx < len(meth) else '?'
                res.append((start, end, cname, mname))
    return res

def main():
    apk, dexname, hexpat = sys.argv[1], sys.argv[2], sys.argv[3]
    pat = bytes.fromhex(hexpat)
    d = zipfile.ZipFile(apk).read(dexname)
    st = strings(d)
    ty = types(d, st)
    ranges = code_ranges(d, st, ty)
    pos = 0
    while True:
        p = d.find(pat, pos)
        if p < 0:
            break
        owner = None
        for (s, e, c, m) in ranges:
            if s <= p < e:
                owner = (c, m)
                break
        print('offset %d (0x%x) owner=%s' % (p, p, owner))
        pos = p + 1

if __name__ == '__main__':
    main()
