import os
import struct
import sys
import zipfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tools'))
import arsc as arscmod

TARGETS = {
    'qs_disabled_color': 0x26000000,
    'qs_disabled_color_legacy': 0x26000000,
    'qs_unavailable_color': 0x26000000,
    'qs_unavailable_color_legacy': 0x26000000,
    'qs_restrict_color': 0x26000000,
    'qs_restrict_color_legacy': 0x26000000,
    'qs_card_disabled_color': 0x26000000,
    'qs_card_disabled_color_legacy': 0x26000000,
    'qs_card_unavailable_color': 0x26000000,
    'qs_card_unavailable_color_legacy': 0x26000000,
    'qs_card_restricted_color': 0x26000000,
    'qs_card_restricted_color_legacy': 0x26000000,
    'external_entry_background_color': 0x26000000,
    'external_entry_background_color_legacy': 0x26000000,
    'toggle_slider_progress_background_color': 0x26000000,
    'toggle_slider_progress_background_color_legacy': 0x26000000,
    'detail_panel_background_color': 0xE5343435,
    'detail_panel_header_text_color': 0xFFFFFFFF,
    'detail_panel_button_text_color': 0xFFFFFFFF,
    'miui_dnd_toast_text_color': 0xFFFFFFFF,
    'miui_volume_dnd_text_color': 0xFFFFFFFF,
    'toggle_slider_top_text_color': 0xFFFFFFFF,
    'toggle_slider_icon_color': 0xFF959595,
    'miuix_appcompat_menu_list_text_color_normal_light': 0xFFFFFFFF,
    'miuix_appcompat_menu_list_text_color_pressed_light': 0xFFFFFFFF,
    'miuix_appcompat_menu_list_text_color_disabled_light': 0xFFFFFFFF,
    'miuix_appcompat_menu_list_text_color_normal_dark': 0xFFFFFFFF,
    'miuix_appcompat_menu_list_text_color_pressed_dark': 0xFFFFFFFF,
    'miuix_appcompat_dropdown_popup_list_text_color_normal_light': 0xFFFFFFFF,
    'miuix_appcompat_dropdown_popup_list_text_color_pressed_light': 0xFFFFFFFF,
    'miuix_appcompat_dropdown_popup_list_text_color_disabled_light': 0xFFFFFFFF,
    'control_center_universal_secondary_text_color': 0xFFFFFFFF,
    'control_center_universal_text_disabled_color': 0xFFFFFFFF,
    'control_primary_text': 0xFFFFFFFF,
    'control_primary_text_alpha': 0xFFFFFFFF,
    'customize_panel_added_secondary_text_color': 0xFFFFFFFF,
    'customize_panel_save_button_text_color': 0xFFFFFFFF,
    'disabled_text_color': 0xFFFFFFFF,
    'external_entry_primary_text_color': 0xFFFFFFFF,
    'external_entry_secondary_text_color': 0xFFFFFFFF,
    'circulate_device_name_text_color': 0xFFFFFFFF,
    'circulate_find_null_text_color': 0xFFFFFFFF,
    'header_customize_subtitle_text_color': 0xFFFFFFFF,
    'header_customize_title_text_color': 0xFFFFFFFF,
    'header_date_text_color': 0xFFFFFFFF,
    'header_privacy_container_text_color': 0xFFFFFFFF,
    'header_text_color': 0xFFFFFFFF,
    'media_player_artist_text_color': 0xFFFFFFFF,
    'media_player_empty_state_text_color': 0xFFFFFFFF,
    'media_player_title_text_color': 0xFFFFFFFF,
    'miplay_bluetooth_share_subTitle_text_color': 0xFFFFFFFF,
    'miplay_bluetooth_share_title_text_color': 0xFFFFFFFF,
    'miplay_detail_header_hint_text_color': 0xFFFFFFFF,
    'miplay_detail_header_subtitle_text_color': 0xFFFFFFFF,
    'miplay_detail_item_playing_info_text_color': 0xFFFFFFFF,
    'miplay_qs_control_detail_header_title_text_color': 0xFFFFFFFF,
    'miui_timer_text_color': 0xFFFFFFFF,
    'miui_volume_dnd_popup_close_text_color': 0xFFFFFFFF,
    'miui_volume_dnd_popup_text_color': 0xFFFFFFFF,
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
                print('%-45s [%-8s] #%08x -> #%08x' % (name, r['cfg'], r['data'], target))
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


if __name__ == '__main__':
    main()
