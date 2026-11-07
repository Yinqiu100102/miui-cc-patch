#!/system/bin/sh
MODDIR=${0%/*}
TARGET=$(ls -d /data/app/*/miui.systemui.plugin-*/base.apk 2>/dev/null | head -n 1)
[ -n "$TARGET" ] && mount -o bind "$MODDIR/base.patched.apk" "$TARGET"
SYSUI=/system_ext/priv-app/MiuiSystemUI/MiuiSystemUI.apk
[ -f "$SYSUI" ] && mount -o bind "$MODDIR/systemui.patched.apk" "$SYSUI"
