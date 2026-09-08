# 第一幕场景 03：完整剧情与界面批次

## 内容

- 完成第一幕场景 03 的全部 231 条玩家剧情文本。
- 翻译 `Config/button.datu8` 的操作提示、`Config/buttonex.datu8` 的扩展操作提示。
- 翻译 `Config/event.datu8` 的各幕章节标题，以及 `Config/system.datu8` 中的示例文本和存档标题。
- 内部文件名、版本号、数值和字体元数据保持不变。
- 所有译文统一为简体中文，并保留原有控制码。

## 构建结果

补丁目录：

```text
07_build/first-act-scene03-complete-ui/atmosphere
```

主表当前包含 1589 条已译记录。三份 TTC 字体均已补入当前译文所需字形。

离线检查结果：

```text
scenario01_3_story_total=231
scenario01_3_story_translated=231
translated_strings=1589
traditional_characters_remaining=0
missing_from_all_ttc=0
```

## 实机测试

1. 完全关闭游戏后，备份 SD 卡上的 `atmosphere/contents/01003080177CA000`。
2. 将压缩包内的 `atmosphere` 文件夹合并到 SD 卡根目录。
3. 检查标题画面、存档/读档、自动模式、跳过模式、回看记录、设置菜单和各幕章节标题。
4. 从第一幕场景 02 结尾进入场景 03，检查面试、测试条件和匂宫与环的对话。
5. 重点确认按钮提示、中文长句换行、角色名及简体字形显示正常。
