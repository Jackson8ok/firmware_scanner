# AFVS v2.7.0 解压问题诊断指南

**日期**: 2026-09-03  
**问题**: 客户反馈解压遇到问题  
**状态**: 🔍 诊断中  

---

## 📋 问题确认

客户反馈：
> "解压问题，源码应该没问题"

**需要澄清**:
1. 下载的是哪个包？
   - ✅ `firmware_scanner-2.7.0.zip` (29MB) - 正式交付包
   - ⚠️ `afvs-auto-firmware-vulnerability-scanner-2.7.0.zip` (6MB) - GitHub 源码包

2. 解压时遇到的具体错误是什么？
   - ❌ "文件损坏"
   - ❌ "路径太长"
   - ❌ "权限不足"
   - ❌ 其他（请提供完整错误信息）

3. 使用什么工具解压？
   - Windows: 资源管理器 / 7-Zip / WinRAR / Bandizip
   - macOS: 归档实用工具 / The Unarchiver / Keka
   - Linux: `unzip` / `7z`

---

## 🔍 常见解压问题及解决方案

### 问题 1: 文件损坏

**症状**:
```
❌ 文件已损坏
❌ CRC 校验失败
❌ Unexpected end of archive
```

**原因**: 下载不完整（网络中断）

**解决方案**:
```bash
# 1. 验证文件大小
# Windows PowerShell:
(Get-Item firmware_scanner-2.7.0.zip).Length / 1MB

# macOS/Linux:
ls -lh firmware_scanner-2.7.0.zip

# 应该显示约 29MB。如果明显偏小，说明下载不完整。

# 2. 重新下载
# 使用浏览器下载管理器或 wget/curl
wget https://github.com/Jackson8ok/afvs-auto-firmware-vulnerability-scanner/releases/download/v2.7.0/firmware_scanner-2.7.0.zip

# 3. 验证 SHA256（如果提供）
sha256sum firmware_scanner-2.7.0.zip
```

---

### 问题 2: 路径太长 (Windows)

**症状**:
```
❌ 路径超过最大长度限制
❌ Cannot create file: ...\scanner\...\very_long_path.py
```

**原因**: Windows 默认路径限制为 260 字符

**解决方案**:

**方法 A**: 使用 7-Zip（推荐）
1. 安装 7-Zip: https://www.7-zip.org/
2. 右键文件 → 7-Zip → Extract Here
3. 7-Zip 自动处理长路径

**方法 B**: 启用 Windows 长路径支持
1. 运行 `gpedit.msc`
2. 计算机配置 → 管理模板 → 系统 → 文件系统
3. 启用"启用 Win32 长路径"
4. 重启电脑

**方法 C**: 解压到短路径
```bash
# 不要解压到桌面或深层目录
# 直接解压到 C:\afvs\
mkdir C:\afvs
cd C:\afvs
# 然后解压
```

---

### 问题 3: 权限不足

**症状**:
```
❌ Access denied
❌ 拒绝访问
❌ Permission denied
```

**解决方案**:
```bash
# Windows: 以管理员身份运行解压工具
# macOS/Linux: 使用 sudo 或修改权限

# Linux/macOS 解压后修复权限
chmod -R 755 firmware_scanner/
```

---

### 问题 4: 解压工具不兼容

**症状**:
```
❌ 不支持的压缩方法
❌ Unknown compression method
```

**解决方案**:
- **Windows**: 使用 7-Zip 或 WinRAR（不要用系统自带）
- **macOS**: 使用 The Unarchiver 或 Keka（不要用系统自带归档工具）
- **Linux**: 使用 `unzip` 或 `7z`

```bash
# Linux 推荐命令
7z x firmware_scanner-2.7.0.zip
# 或
unzip firmware_scanner-2.7.0.zip
```

---

## ✅ 验证解压成功

解压后，检查以下内容：

### 1. 目录结构
```
firmware_scanner/
├── scanner/          # ✅ 必须有（11 个文件）
├── services/         # ✅ 必须有（含 sbom/ 子目录）
├── tests/            # ✅ 必须有
├── api/              # ✅ 必须有
├── frontend/         # ✅ 必须有
├── RELEASE_NOTES_v2.7.0.md  # ✅ 必须有
└── ...
```

### 2. 核心文件检查
```bash
# Linux/macOS
ls -la firmware_scanner/scanner/engine.py
# 应该显示约 68KB

ls -la firmware_scanner/services/sbom/sbom_fusion.py
# 应该显示约 12KB
```

```powershell
# Windows PowerShell
(Get-Item "firmware_scanner\scanner\engine.py").Length
# 应该显示约 68000
```

### 3. 冒烟测试
```bash
cd firmware_scanner
python3 -c "from scanner.engine import FirmwareScanner; print('✅ 加载成功')"
```

---

## 📊 两种包的解压对比

| 项目 | GitHub 源码包 (6MB) | 正式交付包 (29MB) |
|------|-------------------|-----------------|
| 解压后根目录 | `afvs-auto-firmware-vulnerability-scanner-2.7.0/` | `firmware_scanner/` |
| 运行 `import scanner` | ❌ 失败（路径不匹配） | ✅ 成功 |
| 推荐解压工具 | 7-Zip / WinRAR | 7-Zip / WinRAR |
| 预计解压时间 | ~5 秒 | ~15 秒 |

---

## 🎯 建议操作

### 立即执行

1. **确认下载的包**
   - 检查文件名：应该是 `firmware_scanner-2.7.0.zip`
   - 检查大小：应该是 ~29MB
   - 如果不是，重新下载

2. **更换解压工具**
   - Windows: 安装 7-Zip
   - macOS: 安装 The Unarchiver
   - Linux: 使用 `7z x` 命令

3. **解压到短路径**
   - Windows: `C:\afvs\`
   - macOS/Linux: `/tmp/afvs/` 或 `~/afvs/`

4. **验证解压结果**
   - 检查 `scanner/engine.py` 是否存在
   - 执行冒烟测试

### 如果仍有问题

**请提供以下信息**:
1. 下载的文件名和大小
2. 使用的解压工具和版本
3. 完整的错误信息（截图或文字）
4. 解压后的目录结构（`tree -L 2` 或截图）

---

## 📞 联系方式

**维护者**: 攻城狮阿信 [Jackson]  
**邮箱**: zhu80k@163.com  
**GitHub**: https://github.com/Jackson8ok/afvs-auto-firmware-vulnerability-scanner

---

**结论**: 请确认下载的是正确的交付包 (`firmware_scanner-2.7.0.zip`, 29MB)，并使用 7-Zip 等专业工具解压到短路径。
