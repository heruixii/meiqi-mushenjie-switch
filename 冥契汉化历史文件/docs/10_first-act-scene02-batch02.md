# 第一幕场景 02：批次 02

## 内容

- `Script/scenario01_2.binu8`：双叶询问《哈姆雷特》、剧团准备游击演出、演出开始，以及进入高潮前的剧情。
- 继续使用电脑端常用的简体中文角色名。
- 所有新增译文统一为简体中文，保留原文中的控制码和内部演出标识规则。

本批次新增 73 条译文，主翻译表累计 811 条已翻译记录。

## 构建结果

补丁目录：

```text
07_build/first-act-scene02-batch02/atmosphere
```

构建内容包含第一批和第二批的全部已完成文件，字体补丁也会同步更新。所有译文中的汉字和中文标点均使用简体中文字体字形，不再复用原游戏的繁体/日文字形。当前离线校验结果：

```text
translated_strings=811
control_code_mismatches=0
characters_checked=2829
missing_from_all_ttc=0
traditional_characters_remaining=0
localized_non_ascii_glyphs=902
```

## 实机测试重点

1. 关闭游戏后，备份 SD 卡上的 `atmosphere/contents/01003080177CA000`。
2. 将本批次压缩包内的 `atmosphere` 合并到 SD 卡根目录。
3. 从第一幕开场重新进入，确认上一批内容仍正常。
4. 检查《哈姆雷特》开演前的对话、舞台演出文字、观众反应和长句换行。
