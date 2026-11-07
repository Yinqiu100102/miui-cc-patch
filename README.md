# MIUI / HyperOS 控制中心插件补丁

针对 **HyperOS 1 控制中心插件**（`miui.systemui.plugin`）的逆向与补丁记录，
示例目标：**只把大卡片（大磁贴）的图标放大，小磁贴保持不变**。

> Reverse-engineering notes and a patching toolkit for the HyperOS 1 control-center plugin
> (`miui.systemui.plugin`). The worked example enlarges only the *big card* icon without
> touching the small tiles.

验证环境：Redmi 8（`olive`，720×1520，300dpi）+ MIUI 14 / HyperOS 1 控制中心插件 `15.0.1.19.1`。

---

## 1. 背景：控制中心是一个独立 APK

HyperOS 1 的控制中心不在 SystemUI 里，而是 `miui.systemui.plugin` 这个插件 APK，
由 SystemUI 进程加载：

```sh
adb shell dumpsys package miui.systemui.plugin | grep -E 'versionName|codePath'
adb shell dumpsys window | grep mCurrentFocus        # 打开控制中心后是 control_center
```

## 2. 先找「大卡片图标」的尺寸来源

`15.0.1.19.1` 相比 14.x 重写了大磁贴：**`BigTileView` / `BigTileIconView` 已被删除**，
现在用的是 `QSCardItemView` / `QSCardItemIconView`（小磁贴是 `QSTileItemView` / `QSTileItemIconView`）。

所以 14.x 时代改 `qs_control_big_tile_icon_size` 的老办法**完全无效**——
那个 dimen 还在，但渲染路径已经不读它了。

反编译确认（`QSCardItemIconView`）：

```java
// updateResources()
this.iconColor   = pluginContext.getColor(R.color.qs_icon_enabled_color);
...
this.customTileSize = pluginContext.getResources().getDimension(R.dimen.qs_tile_item_icon_inner_size);   // 30dp
this.tileSize       = pluginContext.getResources().getDimension(R.dimen.control_center_universal_1_row_size); // 71.5dp

// getProperDrawable()
float f = drawable instanceof AnimatedVectorDrawable ? tileSize : customTileSize;
```

图标最终被塞进 `LayerDrawable` 并 `setLayerSize(0, f, f)`，**居中**绘制。
也就是说：**图标的实际绘制尺寸由这个 dimen 决定，而不是 ImageView 的尺寸**。
大卡片里 icon view 是 68dp（127px），但 glyph 只有 30dp（56px）——这就是「图标看着很小」的原因。

## 3. 为什么不能只改资源

`qs_tile_item_icon_inner_size` **同时被大卡片和小磁贴使用**：
`QSTileItemIconView` 也在 `updateResources()` 里读同一个 dimen。

所以：

```sh
python3 tools/arsc.py base.apk set qs_tile_item_icon_inner_size 56dp   # ❌ 所有图标一起变大
```

实测（56dp）：大卡片图标变大，**所有小磁贴图标也跟着变大**——不是想要的效果。

## 4. 正确做法：改 dex 里的一条指令

`QSCardItemIconView.updateResources()` 里那一行字节码是：

```
sget v1, Lmiui/systemui/controlcenter/R$dimen;.qs_tile_item_icon_inner_size:I   // field@0x3649
```

把这条 `sget` 的**字段索引**换成 `control_center_universal_1_row_size`（`field@0x3186`），
这样只有大卡片读到 71.5dp，小磁贴仍然读 30dp：

```
sget v1, Lmiui/systemui/controlcenter/R$dimen;.control_center_universal_1_row_size:I
```

字节层面（`sget` 是 `60 AA BBBB`，小端）：

| | 字节 |
|---|---|
| 原指令 | `60 01 49 36`（field@0x3649） |
| 补丁后 | `60 01 86 31`（field@0x3186） |

结果：大卡片图标 30dp(56px) → 71.5dp(134px)，小磁贴保持原样。

## 5. 工具链

| 文件 | 作用 |
|---|---|
| `tools/dexfind.py` | 在 dex 里按字节模式搜索，并反查**该偏移属于哪个类的哪个方法**（自己解析 `class_defs` / `class_data` / `code_item`，不依赖 dexdump） |
| `tools/dexfield.py` | 按字段名查 `field@` 索引（本例用来确认 `qs_tile_item_icon_inner_size` = `field@0x3649`） |
| `tools/dexpatch.py` | 改 dex 字节 + **重算 SHA-1 签名与 Adler-32 校验和** + 按原压缩方式重新打包 APK |

### 定位步骤

```sh
# 1. 哪个 dex 里有这个类
python3 - <<'PY'
import zipfile
z = zipfile.ZipFile('base.apk')
for n in z.namelist():
    if n.startswith('classes') and n.endswith('.dex'):
        d = z.read(n)
        if b'QSCardItemIconView' in d:
            print(n, len(d))
PY

# 2. 反汇编看具体指令（也可以直接用 dexdump）
unzip -o base.apk classes2.dex
dexdump -d classes2.dex > dump.txt
grep -n -A40 "QSCardItemIconView;)" dump.txt | head -60

# 3. 确认字段索引
python3 tools/dexfield.py base.apk classes2.dex qs_tile_item_icon_inner_size
#   field@35a2  Lmiui/systemui/controlcenter/R$dimen; -> qs_control_big_tile_icon_size : I
python3 tools/dexfield.py base.apk classes2.dex control_center_universal_1_row_size
#   field@3186  ...
```

### 打补丁

```sh
python3 tools/dexpatch.py base.apk classes2.dex 0x1aedc4 60014936 60018631 -o base.patched.apk
zipalign -f 4 base.patched.apk base.aligned.apk
```

> `0x1aedc4` 是这个具体版本的偏移，**换版本一定会变**，必须重新定位。
> `dexpatch.py` 会先校验 `old-hex`，不匹配就中止，避免打错位置。

### 为什么必须修 dex 头

DEX 头里有两层校验：

- `offset 8`：**Adler-32**（覆盖 `bytes[12:]`）
- `offset 12`：**SHA-1**（覆盖 `bytes[32:]`）

只改指令不修头部，ART 校验会失败（轻则重新校验、重则拒绝加载，表现为 SystemUI 崩溃/控制中心不显示）。
`dexpatch.py` 的 `fix_header()` 就是干这件事。

## 6. 部署

插件是**平台签名**的（`com.android.systemui.permission.PLUGIN`），改过的包**无法重新签名**，
所以只能「就地覆盖」已安装的 APK，保留原签名与 SELinux 上下文：

```sh
# 备份原始 base.apk
adb shell su -c 'cp <codePath>/base.apk /data/local/tmp/base.orig.apk'

# 覆盖 + 重启 SystemUI
adb push base.aligned.apk /data/local/tmp/base.new.apk
adb shell su -c 'cat /data/local/tmp/base.new.apk > <codePath>/base.apk'
adb shell su -c 'killall com.android.systemui'
```

`<codePath>` 用 `dumpsys package miui.systemui.plugin | grep codePath` 取。
注意用 `cat >` 而不是 `cp`，以保持文件 inode / 属主 `system:system` 644 不变。

**回滚**：把 `/data/local/tmp/base.orig.apk` 用同样的方式写回去，再 `killall com.android.systemui`。

## 7. 其它发现（同版本）

- 控制中心的 window 名是 `control_center`，**不是** `NotificationShade`；后者在这个版本里是不可见的。
- `uiautomator dump` 对控制中心**无效**（`ERROR: could not get idle state`），因为它持续刷新帧。
  自动化验证只能靠 `screencap` + 像素分析，或直接 `adb shell input swipe 620 5 620 1200 350` 打开后截图。
- 大卡片的 icon view 尺寸来自 `qs_tile_item_icon_size`（68dp），glyph 尺寸来自上面那两个 dimen，
  两者独立——**只改 icon view 尺寸不会让图标变大**。

## License

MIT
