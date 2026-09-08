# 工具和密钥配置

## 已准备工具

### NSZ

```text
版本：5.0.0
路径：.venv\Scripts\nsz.exe
用途：NSZ/NCZ 压缩层处理、NSP 容器处理
```

### hactool

```text
版本：1.4.0
路径：tools\hactool\hactool.exe
用途：NCA 信息查看、NCA 解密、RomFS/ExeFS 提取
来源：https://github.com/SciresM/hactool/releases/tag/1.4.0
```

下载包 SHA-256：

```text
36E9A221C8A7949C86ADA9388EB703C90663AEDFE9F65B6032429614C5E1ABE8
```

解压后的 `hactool.exe` SHA-256：

```text
01E6CCB916C74071645DF84F13E05D0185C9B2F5D748E469C84A157A53395CF9
```

## 密钥要求

需要你从自己的 Switch 环境合法导出的兼容 hactool 密钥文件。不要把密钥文件放进项目目录，也不要发到聊天中。

本项目的自动解包脚本使用：

```text
D:\switch游戏\个人汉化\密钥\prod.keys
```

也可以在命令中使用 `--keys` 或 `-k` 指定本机密钥文件路径。密钥文件不会被复制到构建目录，也不应上传或提交到版本库。

当前检查结果：已发现并确认上述 `prod.keys` 文件存在。

## 解包顺序

```text
NSZ
→ NSP/NCA
→ 识别 Program NCA
→ 提取 RomFS
→ 扫描文本、字体和资源
```

不要直接对原始 NSZ 执行写入操作。输出应放在：

```text
01_extracted\container
01_extracted\romfs
```

## 有密钥后的命令

以下命令只对工作副本操作。执行前确认 `%USERPROFILE%\.switch\prod.keys` 是你自己的合法导出文件。

```powershell
$project = 'D:\switch游戏\冥契的牧神节（未汉化）'
$sourceDir = 'D:\switch游戏\个人汉化\冥契的牧神节 Meikei no Lupercalia\本体'
$nsz = Get-ChildItem -LiteralPath $sourceDir -File -Filter '*.nsz' | Select-Object -First 1 -ExpandProperty FullName
$key = 'D:\switch游戏\个人汉化\密钥\prod.keys'

New-Item -ItemType Directory -Force -Path "$project\01_extracted\container" | Out-Null

& "$project\.venv\Scripts\nsz.exe" `
  --keys $key `
  --output "$project\01_extracted\container" `
  -D $nsz
```

解压完成后，先查看每个 NCA 的信息，找出 `ContentType: Program` 的 NCA：

```powershell
$nca = Get-ChildItem -LiteralPath "$project\01_extracted\container" -File -Filter '*.nca'
foreach ($file in $nca) {
  Write-Host "==== $($file.Name) ===="
  & "$project\tools\hactool\hactool.exe" -k $key -i $file.FullName
}
```

找到 Program NCA 后再提取 RomFS：

```powershell
New-Item -ItemType Directory -Force -Path "$project\01_extracted\romfs" | Out-Null
& "$project\tools\hactool\hactool.exe" `
  -k $key `
  --romfsdir "$project\01_extracted\romfs" `
  '<Program NCA 的完整路径>'
```

Program NCA 的具体文件名需要根据 `hactool -i` 输出确认，不能凭文件名猜测。
