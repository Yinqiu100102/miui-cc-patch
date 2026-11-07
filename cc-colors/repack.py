import sys
import zipfile

src, dex, out = sys.argv[1], sys.argv[2], sys.argv[3]
with zipfile.ZipFile(src) as z, zipfile.ZipFile(out, 'w') as zo:
    for info in z.infolist():
        data = open(dex, 'rb').read() if info.filename == 'classes2.dex' else z.read(info.filename)
        zi = zipfile.ZipInfo(info.filename, date_time=info.date_time)
        zi.compress_type = info.compress_type
        zi.external_attr = info.external_attr
        zi.internal_attr = info.internal_attr
        zi.create_system = info.create_system
        zo.writestr(zi, data)
print('repacked', out)
