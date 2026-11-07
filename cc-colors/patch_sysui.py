import os
import struct
import sys
import zipfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tools'))
import arsc as arscmod

TARGETS = {
    'qs_detail_item_primary_text_color_plugin': 0xFFFFFFFF,
    'qs_detail_item_secondary_text_color_plugin': 0xFFFFFFFF,
    'qs_detail_item_inactivated_color_plugin': 0xFFFFFFFF,
    'qs_detail_item_icon_color': 0xFFFFFFFF,
    'qs_detail_item_icon_color_2': 0xFFFFFFFF,
    'qs_detail_item_icon_color_secondary': 0xFFFFFFFF,
    'qs_detail_item_icon_selected_color_2': 0xFFFFFFFF,
    'qs_control_detail_header_text_color_plugin': 0xFFFFFFFF,
    'qs_control_detail_more_button_color': 0xFFFFFFFF,
    'qs_detail_buttons_text_color': 0xFFFFFFFF,
    'qs_detail_title_text_color': 0xFFFFFFFF,
    'miuix_appcompat_menu_list_text_color_normal_light': 0xFFFFFFFF,
    'miuix_appcompat_menu_list_text_color_pressed_light': 0xFFFFFFFF,
    'miuix_appcompat_menu_list_text_color_disabled_light': 0xFFFFFFFF,
    'miuix_appcompat_menu_list_text_color_normal_dark': 0xFFFFFFFF,
    'miuix_appcompat_menu_list_text_color_pressed_dark': 0xFFFFFFFF,
}
COLOR_TYPES = (0x1c, 0x1d, 0x1e, 0x1f)


def main():
    src, out = sys.argv[1], sys.argv[2]
    z = zipfile.ZipFile(src)
    arsc = bytearray(z.read('resources.arsc'))
    rows = arscmod.parse(bytes(arsc))
    total = 0
    for name, target in TARGETS.items():
        hit = 0
        for r in rows:
            if r['tname'] == 'color' and r['name'] == name and r['dtype'] in COLOR_TYPES:
                struct.pack_into('<I', arsc, r['doff'], target)
                hit += 1
                total += 1
                print('%-55s [%-8s] #%08x -> #%08x' % (name, r['cfg'], r['data'], target))
        if hit == 0:
            print('WARN no entry for %s' % name)
    if total == 0:
        raise SystemExit('nothing patched')
    with zipfile.ZipFile(out, 'w') as zo:
        for info in z.infolist():
            data = bytes(arsc) if info.filename == 'resources.arsc' else z.read(info.filename)
            zi = zipfile.ZipInfo(info.filename, date_time=info.date_time)
            zi.compress_type = info.compress_type
            zi.external_attr = info.external_attr
            zi.internal_attr = info.internal_attr
            zi.create_system = info.create_system
            zo.writestr(zi, data)
    print('patched %d entries -> %s' % (total, out))


main()
