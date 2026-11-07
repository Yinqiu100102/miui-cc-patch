import sys
import zipfile

src, entry, datafile, out = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
newdata = open(datafile, 'rb').read()
with zipfile.ZipFile(src) as z, zipfile.ZipFile(out, 'w') as zo:
    for info in z.infolist():
        data = newdata if info.filename == entry else z.read(info.filename)
        zi = zipfile.ZipInfo(info.filename, date_time=info.date_time)
        zi.compress_type = info.compress_type
        zi.external_attr = info.external_attr
        zi.internal_attr = info.internal_attr
        zi.create_system = info.create_system
        zo.writestr(zi, data)
print('repacked', entry, '->', out)
