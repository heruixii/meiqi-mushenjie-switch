# 第一幕开场段：批次 01

## 内容

- 第一幕标题：`第一幕　魔性的绯红`
- `Script/scenario01_1.binu8` 的开场独白和折原冰狐演出
- 濑和环与仓科双叶的校园开场
- 椎名胧、白坂花首次登场
- 角色名沿用 `03_text/glossary/人物名表.csv` 的电脑端常用译名

本批次共新增 175 条剧情/标题译文。连同角色名阶段的 563 条记录，总翻译表当前有 738 条已翻译记录。

## 翻译处理

正文根据连续场景、说话人和角色关系进行人工语境翻译，保留 `@n`、`@v...`、`@vcs...` 控制标记。`Mirai_0000`、`ガラス中`、`映画の横薙ぎ最速`、`EventMode` 等内部标识或演出参数没有擅自翻译。

## 构建结果

补丁目录：

```text
07_build/first-act-opening-batch01/atmosphere
```

构建校验：

```text
translated_strings=738
files_written=98
control_code_mismatches=0
chapter_title_records=10
```

离线扫描结果见 `08_test/first-act-opening-batch01-scan.tsv`。

## Switch 测试

1. 关闭游戏并安全断开 SD 卡。
2. 备份当前 `atmosphere/contents/01003080177CA000` 目录。
3. 用本批次补丁中的 `atmosphere` 合并替换 SD 卡根目录的 `atmosphere`。
4. 启动游戏，确认第一幕标题、开场独白、折原冰狐、濑和环、仓科双叶、椎名胧和白坂花的姓名与对白显示正常。
5. 重点检查中文换行、标点、长句、演剧引号和文本推进。

当前只完成第一幕的开场段，测试通过后继续处理 `scenario01_2` 至 `scenario01_10`。
