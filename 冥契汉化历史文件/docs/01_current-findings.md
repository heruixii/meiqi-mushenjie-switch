# 当前勘察记录

## 2026-09-01

### 输入文件

扫描目录：

```text
D:\switch游戏\冥契的牧神节 Meikei no Lupercalia
```

发现：

```text
本体\冥契のルペルカリア [01003080177CA000][v0].nsz
```

文件大小：`2036413648 bytes`

文件 SHA-256：

```text
A2C39886C302EDEADAC9AAC1E265B69E2B13DF82B819E1C4F92E64022759023D
```

文件头：`PFS0`

### 当前结论

1. 这是压缩后的 Switch 软件包，不能直接像普通文件夹一样寻找文本。
2. 可以先读取 PFS0 目录，确认内部包含哪些 NCA 和元数据文件。
3. 要进一步解包加密内容，需要使用合法来源的本机密钥和对应工具。
4. 当前没有发现更新包，因此先以 v0 本体为目标。
5. 本机搜索未发现 `nsz`、`7z`、`hactool` 或 `hactoolnet` 工具，需要在下一阶段补齐。

### 尚未确认

- 游戏地区
- 是否需要额外的更新包
- 游戏引擎
- 文本所在 NCA 或资源文件
- 文本编码
- 字体类型
- Switch 版和电脑端汉化的文本对应关系
- 游戏是否支持 LayeredFS 覆盖所需的补丁结构

## 无密钥解包说法核验

结论：说法部分正确，但不能理解为“无需密钥即可提取游戏文本”。

### 不需要密钥的部分

- PFS0 是容器格式，可以读取文件名、大小和偏移。
- 当前项目已经在不使用密钥的情况下读取了 NSZ 顶层 PFS0 目录。
- 某些工具可以只处理 NSZ/NCZ 的压缩层，把 NCZ 还原成 NSP/NCA 容器。这一步仍然不会解密游戏内容。

### 仍需要密钥的部分

- 从 NCA 读取和提取 RomFS。
- 解密 NCA 的 ExeFS、RomFS 或其他内容分区。
- 读取大多数游戏资源、文本、字体和脚本。
- 对加密内容进行完整校验、解析或重打包。

### 证据

- [NSZ 官方 README](https://github.com/nicoboss/nsz)：说明 NSZ 是无损压缩/解压工具，保留技术保护措施；README 的 Requirements 明确要求用户提供兼容 hactool 的密钥文件。
- [NSZ 官方用法](https://github.com/nicoboss/nsz/blob/master/docs/usage.md)：提供 `-D` 解压和 `--extract` 容器提取命令，但这不等于解密 NCA。
- [hactool 官方 README](https://github.com/SciresM/hactool)：说明工具用于查看、解密和提取 NCA，并提供 `--keyset`、`--titlekey`、`--contentkey` 和 `--romfsdir` 参数。
- [Switchbrew NCA 格式说明](https://switchbrew.org/wiki/NCA)：明确写出原始 NCA 整体加密，除可能存在的 logo section 外，其他内容需要先得到明文才能解析。

因此，网上所谓“免密钥解包”通常指的是查看容器目录、还原压缩层，或者处理已经被其他步骤解密过的文件，不代表可以直接拿到本游戏的 RomFS 和文本。
