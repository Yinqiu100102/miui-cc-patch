import sys, struct, zipfile
import dexfind

apk, dexname, want = sys.argv[1], sys.argv[2], sys.argv[3]
d = zipfile.ZipFile(apk).read(dexname)
st = dexfind.strings(d)
ty = dexfind.types(d, st)
n = struct.unpack_from('<I', d, 0x50)[0]
off = struct.unpack_from('<I', d, 0x54)[0]
for i in range(n):
    cls_idx, type_idx, name_idx = struct.unpack_from('<HHI', d, off + i * 8)
    name = st[name_idx]
    if want in name:
        print('field@%04x  %s -> %s : %s' % (i, ty[cls_idx], name, ty[type_idx]))
