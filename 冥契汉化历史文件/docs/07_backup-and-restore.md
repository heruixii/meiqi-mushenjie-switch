# SD 卡备份与还原说明

## 本次测试前的实际检查结果

检查位置：

```text
SD 卡\atmosphere\contents\01003080177CA000
```

测试前没有找到该 Title ID 文件夹，因此本次没有旧的 LayeredFS 文件需要备份。原版游戏本体没有被修改。

如果以后安装前该目录已经存在，必须先备份本次补丁会覆盖的同名文件：

```text
romfs\Config\button.datu8
romfs\Script\eventmode.binu8
romfs\Script\replaymode.binu8
romfs\Script\scenario01_1.binu8
romfs\Script\title.binu8
```

建议备份到：

```text
D:\switch游戏\个人汉化\还原备份\冥契的牧神节_测试前备份
```

并保持以下结构：

```text
冥契的牧神节_测试前备份\atmosphere\contents\01003080177CA000\romfs\...
```

## 安装最小测试补丁

退出游戏后，将下面目录中的 `atmosphere` 文件夹合并到 SD 卡根目录：

```text
D:\switch游戏\冥契的牧神节（未汉化）\07_build\minimal-switch-test\atmosphere
```

目标位置：

```text
SD 卡\atmosphere
```

复制后应看到：

```text
SD 卡\atmosphere\contents\01003080177CA000\romfs\Config\button.datu8
SD 卡\atmosphere\contents\01003080177CA000\romfs\Script\eventmode.binu8
SD 卡\atmosphere\contents\01003080177CA000\romfs\Script\replaymode.binu8
SD 卡\atmosphere\contents\01003080177CA000\romfs\Script\scenario01_1.binu8
SD 卡\atmosphere\contents\01003080177CA000\romfs\Script\title.binu8
```

## 还原本次测试

本次测试前 Title ID 覆盖目录不存在，所以还原方式是删除本次新建的：

```text
SD 卡\atmosphere\contents\01003080177CA000
```

删除前必须确认：

- 该文件夹确实由本次测试创建；
- 文件夹内没有其他 Mod 或个人文件；
- 游戏已经完全退出。

如果将来安装前该文件夹原本存在，则不要删除整个 Title ID 文件夹：

- 原本存在的文件：用备份文件复制回原位置并覆盖；
- 原本不存在的文件：删除补丁新增的对应文件；
- 只有在目录为空且确认不再需要时，才删除空的上级目录。

## 不要操作的目录

不要删除或覆盖：

```text
SD 卡\Nintendo
SD 卡\emuMMC
SD 卡\bootloader
SD 卡\atmosphere\contents\其他 Title ID
```

密钥文件不需要、也不应该复制到 SD 卡。
