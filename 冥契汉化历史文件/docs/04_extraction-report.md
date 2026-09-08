# 冥契的牧神节：本体提取报告

更新时间：2026-09-01

## 输入与版本

- Title ID：`01003080177CA000`
- 版本：`v0`
- 输入文件：`D:\switch游戏\个人汉化\冥契的牧神节 Meikei no Lupercalia\本体\冥契のルペルカリア [01003080177CA000][v0].nsz`
- 原始 NSZ SHA-256：`A2C39886C302EDEADAC9AAC1E265B69E2B13DF82B819E1C4F92E64022759023D`
- 密钥来源：用户提供的本机 `prod.keys`，仅用于本地处理

## 已完成

1. NSZ 已解压为 NSP，输出位于 `01_extracted\container\base.nsp`。
2. NSP 已拆出 6 个条目，NCA 哈希校验通过。
3. 已识别 `187827a3a33f4a51894d422540d4137f.nca` 为 Program NCA。
4. 已提取 Program NCA 的 RomFS 与 ExeFS。
5. 已确认 RomFS 中存在明文 UTF-8 的视觉小说脚本。

## RomFS 统计

| 类型 | 数量 | 总大小 |
|---|---:|---:|
| `.binu8` | 99 | 8.1 MiB |
| `.datu8` | 31 | 237 KiB |
| `.spm` | 290 | 383 KiB |
| `.fnt` | 24 | 69.8 MiB |
| `.png` | 3933 | 1.10 GiB |
| `.opus` | 9327 | 538 MiB |
| `.mp4` | 2 | 352 MiB |

脚本目录为 `RomFS\Script`，共有 99 个 `.binu8`。主线场景按 `scenario01` 至 `scenario09` 及少量 `b` 分支组织。

## 文本解析结论

已确认脚本包含如下结构：

```text
uint32 little-endian stored_length
UTF-8 bytes
NUL
```

`stored_length` 包含末尾 NUL。不同文本池之间可能夹有二进制记录，因此不能把整个文件简单当作连续文本处理。对白中可见 `@v...`、`@n` 等控制标记，翻译时必须原样保留或按规则转换。

已生成：

- `03_text\extracted\binu8-string-table.tsv`：30752 条长度前缀字符串候选
- `03_text\translated\translation-sheet.tsv`：30752 条翻译工作表
- `03_text\translated\scenario01_1-sheet.tsv`：首个场景的 214 条工作表
- `docs\romfs-inventory.csv`：RomFS 文件清单

对应脚本：

- `06_scripts\extract_binu8_strings.py`
- `06_scripts\make_translation_sheet.py`
- `06_scripts\scan_binu8_text.py`

## 字体结论

RomFS 中有 24 个 `.fnt`，文件头为 `FNT`，其中字体图像数据带 zlib 压缩。另有 3 个 `.ttc`。优先检查 `System` 目录下的 `system*.fnt`、`k_*.fnt` 和 `df*.ttc`，先做单字测试，再决定替换位图字库还是切换到可显示中文的字体资源。

## 下一步

1. 解析 `binu8` 的记录表，区分对白、角色名、选项和技术字符串。
2. 检查文本框的换行、控制码和可显示字符范围。
3. 解析一份 `.fnt`，确认字形索引、字符集和压缩块布局。
4. 只制作一个场景、一个角色名和一个菜单项的最小测试补丁。
5. 在 Switch 虚拟系统中验证启动、推进、选项、存档和读档。

当前阶段不要直接批量回写全量翻译，也不要修改 `01_extracted\container` 中的原始容器或 `00_original_reference`。
