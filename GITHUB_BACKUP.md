# GitHub 备份说明

## 仓库性质

这个仓库是本地《冥契的牧神节 / Meikei no Lupercalia》Nintendo Switch 汉化项目的**工程级备份**。

本地项目目录中包含约 64 GB 的历史工作数据，以及约 1.9 GB 的游戏本体。GitHub 备份不等于完整磁盘镜像。

## 已备份

### 最终补丁

- `汉化补丁/09_release/pc-merged-v483/`
- `汉化补丁/09_release/使用方法.md`
- `汉化补丁/09_release/恢复日文方法.md`

重复的 `09_release.rar` 不提交。

### 最终文本

- `冥契汉化历史文件/03_text/translated/translation-sheet.tsv`
- `冥契汉化历史文件/03_text/translated/validation-pc-full-safe-unique.tsv`
- `冥契汉化历史文件/03_text/glossary/人物名表.csv`
- `冥契汉化历史文件/03_text/glossary/术语表.csv`
- `冥契汉化历史文件/03_text/翻译规范.md`

### 工程源码与资料

- `冥契汉化历史文件/06_scripts/`
- `冥契汉化历史文件/docs/`
- `pc_switch_scene_report.tsv`
- `pc_voice_candidates.tsv`
- PC 补丁最终说明文本

## 明确不上传

- `本体/` 下的 NSZ；
- 解包产生的 NSP/NCA；
- PC 游戏 XP3 与语音；
- 原始/解包 RomFS；
- OP/ED 视频；
- `.venv` 和 Python 第三方包；
- `02_work` 中数万份阶段构建；
- `08_test` 测试构建；
- 私有密钥、`prod.keys`、`*.keys`；
- 重复压缩包与完整游戏容器。

## 本地恢复

GitHub 仓库可恢复最终汉化补丁、最终翻译数据和主要工程脚本；若需要从头重新构建，仍需用户自行合法持有对应 Switch 游戏资源及本地工具/密钥环境。
